import asyncio
import json
import httpx
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Callable, Awaitable

from settings.config_loader import config       # Конфиг
from log.logger import logger                   # Логгер
from shared_models import Event                 # Shared типовой event
from storage.storage import Storage             # БД
from engine.analyzer import Analyzer            # Обнаружение аномалий


storage = Storage(  # Импортированный класс БД
    db_path=config._data.get("storage", {}).get("db_path", "storage/sqlite.db"),
    retention_days=config._data.get("storage", {}).get("retention_days", 7)
)

api_port = config._data.get("web", {}).get("api_port", 8000)
http_client = httpx.AsyncClient(base_url=f"http://127.0.0.1:{api_port}")    # For WebSockets

async def periodic_db_flush():
    while True:
        await asyncio.sleep(5)
        await storage.flush()

class PipelineProtocol(asyncio.DatagramProtocol):   # класс для приема UDP от коллекторов на Go
    def __init__(self, pipeline_instance):
        self.pipeline = pipeline_instance

    def datagram_received(self, data, addr):
        message = data.decode('utf-8')                      # raw bytes -> str
        logger.info(f"[PIPELINE] Messaage arrived: {message}")
        logger.info(f"[PIPELINE] Initial data: {data}") 
        asyncio.create_task(self.pipeline.emit(message))    # Создаем задачу в пайплайне

class EventPipeline:
    def __init__(self):
        # Очередь async
        self.queue = asyncio.Queue()
        
        # Реестр подписчиков: какой тип события куда отправлять (через if/else получается дичь)
        self.subscribers: Dict[str, List[Callable[[Event], Awaitable[None]]]] = {
            "metric": [],   # Storage Analyzer WebSocket
            "alert": [],    # WebSocket и Alert Engine
            "anomaly": []   # Logger или доп. анализаторы
        }

    # Input
    async def emit(self, raw_json: str):
        try:
            data = json.loads(raw_json)
            await self.validate(data)
        except json.JSONDecodeError as e:
            logger.error(f"[PIPELINE] Pipeline Input Error: Invalid JSON - {e}")    # метка в логах [PIPELINE] для удобного различия от логов других источников
        except Exception as e:
            logger.error(f"[PIPELINE] Unexpected error during emit: {e}", exc_info=True)

    # For already normalized data (from analyzer)
    async def emit_event(self, event: Event):
        try:
            await self.route(event)
        except Exception as e:
            logger.error(f"[PIPELINE] Error emitting event object: {e}", exc_info=True)

    # Validation
    async def validate(self, data: Dict):
        required_fields = {"type", "source", "data"}
        if not required_fields.issubset(data.keys()):
            logger.warning(f"[PIPELINE] Pipeline Validation Failed: Missing fields in {data}")
            return
        await self.normalize(data)

    # Normalization & Enrichment
    async def normalize(self, data: Dict):
        event = Event(
            type=data["type"],
            source=data["source"],
            data=data["data"],
            metadata=data.get("metadata", {})
        )
        event.metadata["version"] = config._data.get("version", "1.0.0")    # системные метаданные 
        
        await self.route(event)

    # Routing
    async def route(self, event: Event):
        handlers = self.subscribers.get(event.type, [])
        if not handlers:
            logger.debug(f"[PIPELINE] No subscribers for event type: {event.type}")
            return

        for handler in handlers:
            # Кладем задачу в очередь, чтобы не блокировать поток (да, тут все в диком потоке)
            await self.queue.put((handler, event))

    # Dispatch (воркерами)
    async def start_worker(self):
        logger.info("[PIPELINE] Event Pipeline Worker started.")        
        while True:
            handler, event = await self.queue.get()
            try:
                # Вызов async handler
                await handler(event)
            except Exception as e:
                logger.error(f"[PIPELINE] Handler Error ({handler.__name__}): {e}")
            finally:
                self.queue.task_done()
    
    # Запуск севера и инициализация воркера
    async def start_server(self):
        await storage.initialize()
        asyncio.create_task(storage.cleanup_loop())
        asyncio.create_task(periodic_db_flush())

        port = config._data.get("pipeline_port", 5005)
        loop = asyncio.get_running_loop()
        
        logger.info(f"[PIPELINE] Starting UDP Pipeline Server on port {port}...")
        
        # Регистрация UDP эндпоинта в event loop
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: PipelineProtocol(self),
            local_addr=('127.0.0.1', port)
        )
        
        asyncio.create_task(self.start_worker())

        try:
            while True:
                await asyncio.sleep(3600) 
        except asyncio.CancelledError:
            transport.close()

async def storage_handler(event: Event):
    await storage.save_event(asdict(event))

async def websocket_broadcast_handler(event: Event):
    try:
        event_dict = asdict(event)
        await http_client.post("/internal/broadcast", json=event_dict)  # i hate how it breaks the beauty of logs
    except Exception as e:
        logger.error(f"[PIPELINE] WebSocket Broadcast Error: {e}")
        await http_client.aclose()


# Подписки на Events
def setup_subscriptions(storage_handler, websocket_broadcast_handler, analyzer):
    pipeline.subscribers["metric"].append(storage_handler)
    pipeline.subscribers["metric"].append(websocket_broadcast_handler)
    pipeline.subscribers["metric"].append(analyzer.process_metric)

    pipeline.subscribers["alert"].append(storage_handler)
    pipeline.subscribers["alert"].append(websocket_broadcast_handler)


pipeline = EventPipeline()
analyzer = Analyzer(pipeline)


if __name__ == "__main__":    
    try:
        setup_subscriptions(storage_handler, websocket_broadcast_handler, analyzer)
        asyncio.run(pipeline.start_server())
    except KeyboardInterrupt:
        http_client.aclose()    # idk where to close it honestly
        pass
    except Exception as e:
        logger.error(f"[PIPELINE] Pipeline error: {e}", exc_info=True)