import asyncio
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Callable, Awaitable

from settings.config_loader import config       # Конфиг
from log.logger import logger                   # Логгер
from shared_models import Event                 # Shared типовой event
from storage.storage import Storage             # БД


storage = Storage(  # Импортированный класс БД
    db_path=config._data.get("storage", {}).get("db_path", "storage/sqlite.db"),
    retention_days=config._data.get("storage", {}).get("retention_days", 7)
)

async def periodic_db_flush():
    while True:
        await asyncio.sleep(5)
        await storage.flush()

class PipelineProtocol(asyncio.DatagramProtocol):   # класс для приема UDP от коллекторов на Go
    def __init__(self, pipeline_instance):
        self.pipeline = pipeline_instance

    def datagram_received(self, data, addr):
        # raw bytes -> str
        message = data.decode('utf-8')
        logger.info(f"[PIPELINE] {message}") # Пока что оставить, дебаг -> вывод приходящих данных
        # Создаем задачу в пайплайне
        asyncio.create_task(self.pipeline.emit(message))

class EventPipeline:
    def __init__(self):
        # Очередь async
        self.queue = asyncio.Queue()
        
        # Реестр подписчиков: какой тип события куда отправлять (через if/else получается дичь)
        self.subscribers: Dict[str, List[Callable[[Event], Awaitable[None]]]] = {
            "metric": [],   # Storage и Analyzer
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
        # системные метаданные 
        event.metadata["version"] = config._data.get("version", "1.0.0")
        
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

# Подписки на Events
def setup_subscriptions(storage_handler):
    pipeline.subscribers["metric"].append(storage_handler)
    
    pipeline.subscribers["alert"].append(storage_handler)


pipeline = EventPipeline()


if __name__ == "__main__":    
    try:
        setup_subscriptions(storage_handler)
        asyncio.run(pipeline.start_server())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"[PIPELINE] Pipeline error: {e}", exc_info=True)