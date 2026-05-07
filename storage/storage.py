import json
import asyncio
import aiosqlite
from datetime import datetime, timedelta

from log.logger import logger


# Важно: понимать, что запись не производится напрямую в бд, мы записываем своего рода список в буфер и из буфер кидаем запись в бд
class Storage:
    def __init__(self, db_path: str, retention_days: int = 7, batch_size: int = 15):
        self.db_path = db_path
        self.retention_days = retention_days
        self.batch_size = batch_size
        self.buffer = []
        self.lock = asyncio.Lock()

    async def initialize(self): # инициализация бд
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp INTEGER,
                        source TEXT,
                        type TEXT,
                        data TEXT
                    )
                """)
                await db.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)')
                await db.commit()
                logger.info(f"Storage: Database initialized at {self.db_path}. Retention: {self.retention_days} days")
        except Exception as e:
            logger.error(f"Storage: Failed to initialize database: {e}")

    async def save_event(self, event: dict):
        # Фильтр событий на сохранение
        allowed_types = ["metric", "alert", "system"]
        e_type = event.get('type', '')
        
        if not any(e_type.startswith(t) for t in allowed_types):
            return

        async with self.lock:
            self.buffer.append((    # вот собственно *буфер*
                event.get('timestamp'),
                event.get('source'),
                e_type,
                json.dumps(event.get('data'))
            ))

        if len(self.buffer) >= self.batch_size:
            await self.flush()

    async def flush(self):
        if not self.buffer:
            return

        async with self.lock:
            to_save = list(self.buffer)
            self.buffer.clear()         # сохраняем -> чистим -> пишем

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.executemany(   
                    'INSERT INTO events (timestamp, source, type, data) VALUES (?, ?, ?, ?)',
                    to_save
                )
                await db.commit()
                logger.debug(f"Storage: Flushed {len(to_save)} events to SQLite")   # сброс буфера нет смысла писать в файл логов
        except Exception as e:
            logger.error(f"Storage: Failed to flush events: {e}")

    async def cleanup_loop(self):
        logger.info("Storage: Cleanup loop started")
        while True:
            cutoff = int((datetime.now() - timedelta(days=self.retention_days)).timestamp())
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute('DELETE FROM events WHERE timestamp < ?', (cutoff,))
                    await db.commit()
                    if cursor.rowcount > 0:
                        logger.info(f"Storage Cleanup: Removed {cursor.rowcount} old records")
            except Exception as e:
                logger.error(f"Storage Cleanup Error: {e}")
            
            await asyncio.sleep(3600) # Проверка каждый час