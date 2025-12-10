import os
import configparser
import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

import aiomysql
from fastapi import FastAPI, Query, Depends, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn


class CaseSensitiveConfigParser(configparser.ConfigParser):
    def optionxform(self, optionstr):
        return optionstr


class Config:
    """Load DB and settings from config.ini, allowing env overrides."""

    def __init__(self, filename: str = "config.ini"):
        self.config = CaseSensitiveConfigParser()
        self.config.read(filename)

    def db_config(self) -> dict:
        cfg = self.config["database"]
        return {
            "host": os.getenv("DB_HOST", cfg.get("host")),
            "port": int(os.getenv("DB_PORT", cfg.get("port", fallback="3306"))),
            "user": os.getenv("DB_USER", cfg.get("user")),
            "password": os.getenv("DB_PASSWORD", cfg.get("password")),
            "db": os.getenv("DB_NAME", cfg.get("database")),
            "charset": cfg.get("charset", fallback="utf8mb4"),
            "autocommit": True,
            "pool_recycle": 3600
        }

    def articles_table(self) -> str:
        return self.config["settings"].get("arxiv_table")

    def categories(self):
        raw = self.config["settings"].get("categories", "")
        return [c.strip() for c in raw.split(",") if c.strip()]

    def api_key(self) -> str:
        key = os.getenv("API_KEY")
        if not key and self.config.has_section("api"):
            key = self.config["api"].get("key")
        if not key:
            raise RuntimeError("API key not configured. Set API_KEY env or [api].key in config.ini")
        return key

    def server_port(self) -> int:
        if self.config.has_section("server"):
            return int(self.config["server"].get("port", 8000))
        return int(os.getenv("PORT", 8000))


async def create_pool(loop, db_config: dict):
    return await aiomysql.create_pool(loop=loop, **db_config)


config = Config()
app = FastAPI(title="Arxiv Day Data API", version="1.0.0")
app.state.pool = None
app.state.table = config.articles_table()
app.state.api_key = None
SYNC_TTL = timedelta(minutes=15)
SYNC_LOCK = asyncio.Lock()
SYNC_DB_PATH = os.getenv("SYNC_DB_PATH", "sync.db")


async def run_in_thread(fn, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: fn(*args))

# Allow CORS for browser access (sync endpoints need preflight)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_running_loop()
    app.state.pool = await create_pool(loop, config.db_config())
    app.state.api_key = config.api_key()
    await run_in_thread(init_sync_db)


@app.on_event("shutdown")
async def shutdown_event():
    pool = app.state.pool
    if pool:
        pool.close()
        await pool.wait_closed()


async def verify_api_key(
    request: Request,
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    expected = request.app.state.api_key
    if not api_key or api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


async def fetch_latest_date(pool, table: str) -> Optional[str]:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(f"SELECT MAX(DATE(updated)) AS latest_date FROM {table}")
            row = await cur.fetchone()
            return row["latest_date"].strftime("%Y-%m-%d") if row and row["latest_date"] else None


async def count_by_category(pool, table: str, category: str, date: str) -> int:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                f"SELECT COUNT(*) AS count FROM {table} WHERE DATE(updated)=%s AND categories LIKE %s",
                (date, f"%{category}%"),
            )
            row = await cur.fetchone()
            return row["count"] if row else 0


@app.get("/")
async def root(auth=Depends(verify_api_key)):
    return {
        "name": "Arxiv Day Data API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "latest": "/latest",
            "articles": "/articles?date=YYYY-MM-DD&category=cs.AI&page=1&page_size=1000",
            "calendar": "/calendar",
            "categories": "/categories",
            "categories_counts": "/categories/counts?date=YYYY-MM-DD",
            "sync_put": "/sync/{id}",
            "sync_get": "/sync/{id}",
        },
        "auth": "Pass X-API-Key header with the configured key.",
        "note": "All endpoints are read-only. Date defaults to latest when omitted. page_size has no enforced upper limit—use responsibly.",
    }


@app.get("/health")
async def health(auth=Depends(verify_api_key)):
    return {"status": "ok"}


@app.get("/latest")
async def latest(auth=Depends(verify_api_key)):
    pool = app.state.pool
    table = app.state.table
    latest_date = await fetch_latest_date(pool, table)
    if not latest_date:
        return {"date": None, "count": 0}
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                f"SELECT COUNT(*) AS count FROM {table} WHERE DATE(updated)=%s",
                (latest_date,),
            )
            row = await cur.fetchone()
            count = row["count"] if row else 0
    return {"date": latest_date, "count": count}


@app.get("/articles")
async def articles(
    date: Optional[str] = None,
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(200, ge=1),
    auth=Depends(verify_api_key),
):
    pool = app.state.pool
    table = app.state.table

    target_date = date or await fetch_latest_date(pool, table)
    if not target_date:
        return {"date": None, "total": 0, "page": page, "page_size": page_size, "items": []}

    where_clauses = ["DATE(updated)=%s"]
    params = [target_date]
    if category:
        where_clauses.append("categories LIKE %s")
        params.append(f"%{category}%")
    where_sql = " AND ".join(where_clauses)

    offset = (page - 1) * page_size

    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                f"SELECT COUNT(*) AS count FROM {table} WHERE {where_sql}",
                params,
            )
            total = (await cur.fetchone())["count"]

            await cur.execute(
                f"""
                SELECT title, summary, authors, categories, comment, entry_id,
                       journal_ref, updated, CN_title, CN_summary
                FROM {table}
                WHERE {where_sql}
                ORDER BY updated DESC
                LIMIT %s OFFSET %s
                """,
                params + [page_size, offset],
            )
            rows = await cur.fetchall()

    return {
        "date": target_date,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": rows,
    }


@app.get("/calendar")
async def calendar(auth=Depends(verify_api_key)):
    pool = app.state.pool
    table = app.state.table
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(f"SELECT DISTINCT YEAR(updated) AS year FROM {table} ORDER BY year DESC")
            years_data = await cur.fetchall()
            await cur.execute(
                f"SELECT DISTINCT DATE(updated) AS day FROM {table} ORDER BY day DESC"
            )
            days_data = await cur.fetchall()
    years = [row["year"] for row in years_data if row["year"]]
    days = [row["day"].strftime("%Y-%m-%d") for row in days_data if row["day"]]
    return {"years": years, "days": days}


@app.get("/categories")
async def categories(auth=Depends(verify_api_key)):
    return {"categories": config.categories()}


@app.get("/categories/counts")
async def categories_counts(date: Optional[str] = None, auth=Depends(verify_api_key)):
    pool = app.state.pool
    table = app.state.table
    target_date = date or await fetch_latest_date(pool, table)
    if not target_date:
        return {"date": None, "items": []}

    categories = config.categories()
    results = []
    for cat in categories:
        cnt = await count_by_category(pool, table, cat, target_date)
        results.append({"category": cat, "count": cnt})
    return {"date": target_date, "items": results}


def init_sync_db():
    conn = sqlite3.connect(SYNC_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_blobs (
            id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            created_at REAL NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def sync_put_db(sync_id: str, payload: dict):
    now_ts = datetime.utcnow().timestamp()
    conn = sqlite3.connect(SYNC_DB_PATH)
    conn.execute(
        "DELETE FROM sync_blobs WHERE created_at < ?",
        (now_ts - SYNC_TTL.total_seconds(),),
    )
    conn.execute(
        "INSERT OR REPLACE INTO sync_blobs (id, payload, created_at) VALUES (?, ?, ?)",
        (sync_id, json.dumps(payload), now_ts),
    )
    conn.commit()
    conn.close()


def sync_get_db(sync_id: str):
    now_ts = datetime.utcnow().timestamp()
    conn = sqlite3.connect(SYNC_DB_PATH)
    conn.execute(
        "DELETE FROM sync_blobs WHERE created_at < ?",
        (now_ts - SYNC_TTL.total_seconds(),),
    )
    cur = conn.execute(
        "SELECT payload, created_at FROM sync_blobs WHERE id = ?", (sync_id,)
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    payload, created_at = row
    if now_ts - created_at > SYNC_TTL.total_seconds():
        # expired, treat as missing
        return None
    data = json.loads(payload)
    data.setdefault("created_at", datetime.utcfromtimestamp(created_at).isoformat())
    return data


@app.put("/sync/{sync_id}")
async def sync_put(sync_id: str, payload: dict):
    # Basic size guard: reject >2MB payload
    size_est = len(json.dumps(payload))
    if size_est > 2_000_000:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Payload too large")
    required_fields = {"ciphertext", "salt", "iv"}
    if not required_fields.issubset(payload.keys()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing ciphertext/salt/iv")
    try:
        await run_in_thread(sync_put_db, sync_id, payload)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return {"status": "ok", "expires_in_seconds": int(SYNC_TTL.total_seconds())}


@app.get("/sync/{sync_id}")
async def sync_get(sync_id: str):
    try:
        result = await run_in_thread(sync_get_db, sync_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found or expired")
    return result


if __name__ == "__main__":
    # Example: python data_api.py --host 0.0.0.0 --port 8000
    import argparse

    parser = argparse.ArgumentParser(description="Run Arxiv Day Data API")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=config.server_port())
    args = parser.parse_args()

    uvicorn.run("data_api:app", host=args.host, port=args.port, reload=False)
