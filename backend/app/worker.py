from __future__ import annotations

from sqlalchemy import select

from backend.app.database import AsyncSessionLocal, close_db, init_db
from backend.app.models import Book

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from arq import create_pool
from arq.connections import RedisSettings
from redis.asyncio import Redis

from backend.app.services.audiobook_pipeline import (
    assemble_book,
    assemble_chapter,
    generate_chunk_audio,
    prepare_book,
)
from backend.app.services.job_status import (
    JobStatusStore,
)
from backend.app.services.kokoro_tts import (
    KokoroProvider,
)


REDIS_SETTINGS = RedisSettings(
    host="127.0.0.1",
    port=6379,
)


async def startup(ctx: dict) -> None:
    """
    Initialize resources once for the worker process.
    """
    await init_db()
    executor = ThreadPoolExecutor(
        max_workers=1,
        thread_name_prefix="audiobook-worker",
    )

    ctx["executor"] = executor

    redis = Redis.from_url(
        "redis://127.0.0.1:6379",
        decode_responses=True,
    )

    ctx["status_redis"] = redis

    ctx["status_store"] = JobStatusStore(
        redis
    )

    loop = asyncio.get_running_loop()

    print("Loading Kokoro...")

    provider = await loop.run_in_executor(
        executor,
        KokoroProvider,
    )

    ctx["tts_provider"] = provider

    print("Kokoro loaded.")

async def update_book_record(
    book_id: str,
    *,
    status: str,
    stage: str,
    progress: int,
    message: str,
    audiobook_path: str | None = None,
) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Book).where(
                Book.id == book_id
            )
        )

        book = result.scalar_one_or_none()

        if book is None:
            return

        book.status = status
        book.stage = stage
        book.progress = progress
        book.message = message

        if audiobook_path is not None:
            book.audiobook_path = (
                audiobook_path
            )

        await session.commit()

async def shutdown(ctx: dict) -> None:
    """
    Release worker resources.
    """
    redis: Redis = ctx["status_redis"]

    await redis.aclose()

    executor: ThreadPoolExecutor = (
        ctx["executor"]
    )

    executor.shutdown(
        wait=True
    )


async def process_book(
    ctx: dict,
    book_id: str,
    pdf_path: str,
    book_title: str,
    chapter_limit: int | None = None,
) -> dict[str, object]:
    """
    Complete audiobook-generation job.
    """
    status_store: JobStatusStore = (
        ctx["status_store"]
    )

    executor: ThreadPoolExecutor = (
        ctx["executor"]
    )

    provider = ctx["tts_provider"]

    loop = asyncio.get_running_loop()

    book_directory = Path(
        pdf_path
    ).parent

    try:
        await status_store.update(
            book_id,
            status="processing",
            stage="extracting",
            progress=5,
            message="Extracting PDF text",
        )

        await update_book_record(
        book_id,
        status="processing",
        stage="extracting",
        progress=5,
        message="Extracting PDF text",
)

        prepared = await loop.run_in_executor(
            executor,
            prepare_book,
            Path(pdf_path),
            book_directory,
        )

        chapters = prepared.chapters
        chunks = prepared.chunks

        if chapter_limit is not None:
            chapters = chapters[:chapter_limit]

        await status_store.update(
            book_id,
            status="processing",
            stage="chunking",
            progress=15,
            message=(
                f"Prepared {len(chapters)} chapters"
            ),
        )

        await update_book_record(
        book_id,
        status="processing",
        stage="chunking",
        progress=15,
        message=(
            f"Prepared {len(chapters)} chapters"
        ),
)

        total_chunks = sum(
            len(chunks[
                chapter.display_title
            ])
            for chapter in chapters
        )

        completed_chunks = 0

        chapter_audio = []

        for chapter in chapters:
            chapter_chunks = chunks[
                chapter.display_title
            ]

            if chapter_limit is not None:
                # Only process the requested chapter subset.
                pass

            chunk_paths: list[Path] = []

            for chunk in chapter_chunks:
                chunk_directory = (
                    book_directory
                    / "audio"
                    / (
                        f"chapter_"
                        f"{chapter.number:02d}"
                        if chapter.number
                        is not None
                        else "extra_chapter"
                    )
                    / "chunks"
                )

                chunk_directory.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                chunk_path = (
                    chunk_directory
                    / (
                        f"chunk_"
                        f"{chunk.index:04d}.wav"
                    )
                )

                await loop.run_in_executor(
                    executor,
                    functools.partial(
                        generate_chunk_audio,
                        provider=provider,
                        chunk=chunk,
                        output_path=chunk_path,
                        voice="af_heart",
                    ),
                )

                chunk_paths.append(
                    chunk_path
                )

                completed_chunks += 1

                generation_progress = (
                    15
                    + int(
                        (
                            completed_chunks
                            / max(total_chunks, 1)
                        )
                        * 65
                    )
                )

                await status_store.update(
                    book_id,
                    status="processing",
                    stage="generating_audio",
                    progress=min(
                        generation_progress,
                        80,
                    ),
                    message=(
                        f"Generated chunk "
                        f"{completed_chunks}/"
                        f"{total_chunks}"
                    ),
                )

                await update_book_record(
                book_id,
                status="processing",
                stage="generating_audio",
                progress=min(
                        generation_progress,
                        80,
                    ),
                message= (
                        f"Generated chunk "
                        f"{completed_chunks}/"
                        f"{total_chunks}"
                    ),
            )

            chapter_result = (
                await loop.run_in_executor(
                    executor,
                    functools.partial(
                        assemble_chapter,
                        chapter=chapter,
                        chunks=chapter_chunks,
                        chunk_paths=chunk_paths,
                        book_directory=book_directory,
                    ),
                )
            )

            chapter_audio.append(
                chapter_result
            )

        await status_store.update(
            book_id,
            status="processing",
            stage="assembling",
            progress=90,
            message="Building M4B audiobook",
        )

        await update_book_record(
            book_id,
            status="processing",
            stage="assembling",
            progress=90,
            message="Building M4B audiobook",
        )

        audiobook_path = (
            await loop.run_in_executor(
                executor,
                functools.partial(
                    assemble_book,
                    chapters=chapter_audio,
                    book_directory=book_directory,
                    book_title=book_title,
                ),
            )
        )

        await status_store.update(
            book_id,
            status="completed",
            stage="completed",
            progress=100,
            message=str(
                audiobook_path
            ),
        )

        await update_book_record(
            book_id,
            status="completed",
            stage="completed",
            progress=100,
            message=str(audiobook_path),
            audiobook_path=str(audiobook_path),
        )

        return {
            "book_id": book_id,
            "audiobook_path": str(
                audiobook_path
            ),
            "chapter_count": len(
                chapters
            ),
            "chunk_count": total_chunks,
        }

    except Exception as exc:
        await status_store.update(
            book_id,
            status="failed",
            stage="failed",
            progress=0,
            message=str(exc),
        )

        await update_book_record(
            book_id,
            status="failed",
            stage="failed",
            progress=0,
            message=str(exc),
        )

        raise


class WorkerSettings:
    functions = [process_book]

    redis_settings = REDIS_SETTINGS

    on_startup = startup
    on_shutdown = shutdown

    # We have one Apple Silicon inference device.
    max_jobs = 1

    # Audiobook generation can legitimately take a long time.
    job_timeout = 6 * 60 * 60

    # Do not automatically regenerate an expensive audiobook
    # five times after a failure.
    max_tries = 1

    keep_result = 60 * 60