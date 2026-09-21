from __future__ import annotations

from contextlib import asynccontextmanager

from arq import create_pool
from fastapi import FastAPI
from redis.asyncio import Redis

from backend.app.database import (
    close_db,
    init_db,
)
from backend.app.worker import REDIS_SETTINGS
from backend.app.api.books import (
    router as books_router,
)

@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    await init_db()

    app.state.arq_pool = (
        await create_pool(
            REDIS_SETTINGS
        )
    )

    app.state.status_redis = (
        Redis.from_url(
            "redis://127.0.0.1:6379",
            decode_responses=True,
        )
    )

    yield

    await app.state.arq_pool.close()
    await app.state.status_redis.aclose()

    await close_db()


app = FastAPI(
    title="Audiobook AI",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(
    books_router
)

@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Audiobook AI is running"
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok"
    }