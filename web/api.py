import json
import aiosqlite
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from settings.config_loader import config
from log.logger import logger

app = FastAPI()     # `python -m web.api`

origins = ["*"]     # Dunno if we really need CORS here, considering that everything is on localhost, but it's good practise
methods = ["*"]
headers = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=methods,
    allow_headers=headers,
)

DB_PATH = config._data.get("storage", {}).get("db_path", "storage/sqlite.db")

def get_db():
    db_path = config._data.get("storage", {}).get("db_path", "storage/sqlite.db")
    return aiosqlite.connect(f"file:{db_path}?mode=ro", uri=True)

@app.get("/api/status")
async def get_status():
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT COUNT(*) as cnt FROM events"
        async with db.execute(query) as cursor:
            row = await cursor.fetchone()
            return {"total_events": row["cnt"], "status": "online"}

@app.get("/api/metrics/latest")
async def get_latest_metrics(limit: int = 20):
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT source, type, data, timestamp 
            FROM events 
            WHERE type = 'metric' 
            ORDER BY id DESC LIMIT ?
        """
        async with db.execute(query, (limit,)) as cursor:
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                result.append({
                    "source": row["source"],
                    "type": row["type"],
                    "timestamp": row["timestamp"],
                    "data": json.loads(row["data"])
                })
            return result

@app.get("/api/alerts")
async def get_alerts(limit: int = 50):
    async with get_db() as db:
        query = "SELECT * FROM events WHERE type = 'alert' ORDER BY id DESC LIMIT ?"
        async with db.execute(query, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

if __name__ == "__main__":
    port = config._data.get("web", {}).get("api_port", 8000)
    logger.info(f"[API] Starting API Server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)