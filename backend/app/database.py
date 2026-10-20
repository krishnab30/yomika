from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


DATABASE_PATH = Path("storage/audiobook.db")
DATABASE_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

DATABASE_URL = (
    f"sqlite+aiosqlite:///{DATABASE_PATH}"
)


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[
    AsyncSession,
    None,
]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    from backend.app.models import Book

    async with engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.create_all
        )

        # Add the voice column to databases created
        # before narration voice selection existed.
        result = await connection.exec_driver_sql(
            "PRAGMA table_info(books)"
        )

        columns = {
            row[1]
            for row in result.fetchall()
        }

        if "voice" not in columns:
            await connection.exec_driver_sql(
                """
                ALTER TABLE books
                ADD COLUMN voice VARCHAR(50)
                NOT NULL DEFAULT 'af_heart'
                """
            )

async def close_db() -> None:
    await engine.dispose()