import asyncio
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Callable, Awaitable

from settings.config_loader import config
from log.logger import logger
from shared_models import Event


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
        """Определение списка получателей """
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
        port = config._data.get("pipeline_port", 5005)
        loop = asyncio.get_running_loop()
        
        logger.info(f"[PIPELINE] Starting UDP Pipeline Server on port {port}...")
        
        # Регистрация UDP эндпоинта в event loop
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: PipelineProtocol(self),
            local_addr=('127.0.0.1', port)
        )
        
        # Запускаем воркер для обработки очереди
        await self.start_worker()

# Импортируем модули (когда они будут готовы)
# from storage.sqlite import save_to_db
# from engine.analyzer import check_metrics
# from engine.alert import process_alert

# Прописываем логику связей прямо здесь
def setup_subscriptions(storage_func, analyzer_func, alert_func, ws_func):
    pipeline.subscribers["metric"].append(storage_func)
    pipeline.subscribers["metric"].append(analyzer_func)
    
    pipeline.subscribers["alert"].append(alert_func)
    pipeline.subscribers["alert"].append(ws_func)

pipeline = EventPipeline()

if __name__ == "__main__":    
    try:
        asyncio.run(pipeline.start_server())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error("[PIPELINE] Pipeline error: {e}", exc_info=True)


# я пока писал, раз 10 точно вместо "pipeline" писал "pipiline" и меня каждый раз рвало с этого слова. Мб переименовать?