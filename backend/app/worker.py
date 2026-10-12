from __future__ import annotations

import asyncio
import functools
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from arq.connections import RedisSettings
from redis.asyncio import Redis
from sqlalchemy import func, select

from backend.app.database import AsyncSessionLocal, init_db
from backend.app.models import Book, Chapter
from backend.app.services.audiobook_pipeline import (
    assemble_chapter,
    generate_chunk_audio,
    prepare_book,
)
from backend.app.services.job_status import JobStatusStore
from backend.app.services.kokoro_tts import KokoroProvider
from backend.app.services.manifest import write_manifest


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

        await session.commit()


async def update_chapter_record(
    *,
    book_id: str,
    title: str,
    audio_path: str,
    duration_seconds: float,
) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Chapter).where(
                Chapter.book_id == book_id,
                Chapter.title == title,
            )
        )

        chapter = result.scalar_one_or_none()

        if chapter is None:
            return

        chapter.filename = (
            Path(audio_path).name
        )

        chapter.audio_path = audio_path

        chapter.duration_seconds = (
            duration_seconds
        )

        chapter.status = "completed"

        await session.commit()


async def pause_book_record(
    book_id: str,
    status_store: JobStatusStore,
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

        book.status = "paused"
        book.stage = "paused"
        book.message = (
            "Generation paused. Continue generation to resume."
        )

        await session.commit()

    await status_store.update(
        book_id,
        status="paused",
        stage="paused",
        progress=book.progress,
        message=(
            "Generation paused. "
            "Continue generation to resume."
        ),
    )

async def shutdown(ctx: dict) -> None:
    """
    Release worker resources.
    """

    active_book_id = ctx.get(
        "active_book_id"
    )

    if active_book_id is not None:
        await pause_book_record(
            active_book_id,
            ctx["status_store"],
        )

    redis: Redis = ctx["status_redis"]

    await redis.aclose()

    executor: ThreadPoolExecutor = (
        ctx["executor"]
    )

    executor.shutdown(
        wait=True
    )

async def create_chapter_records(
    book_id: str,
    chapters: list,
) -> None:
    async with AsyncSessionLocal() as session:
        existing_result = await session.execute(
            select(Chapter).where(
                Chapter.book_id == book_id
            )
        )

        existing_chapters = (
            existing_result.scalars().all()
        )

        for existing in existing_chapters:
            await session.delete(existing)

        for chapter in chapters:
            session.add(
                Chapter(
                    book_id=book_id,
                    chapter_number=chapter.number,
                    title=chapter.title,
                    status="pending",
                )
            )

        book = await session.get(
            Book,
            book_id,
        )

        if book is not None:
            book.chapter_count = len(
                chapters
            )

        await session.commit()


async def process_book(
    ctx: dict,
    book_id: str,
    pdf_path: str,
    book_title: str,
    chapter_limit: int | None = None,
    resume: bool = False,
) -> dict[str, object]:
    """
    Complete audiobook-generation job.
    """
    status_store: JobStatusStore = (
        ctx["status_store"]
    )

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Book).where(
                Book.id == book_id
            )
        )

        book = result.scalar_one_or_none()

        if book is None:
            return {
                "book_id": book_id,
                "skipped": True,
                "reason": "Book not found",
            }

        existing_completed_count = await session.scalar(
            select(
                func.count(Chapter.id)
            ).where(
                Chapter.book_id == book_id,
                Chapter.status == "completed",
            )
        )

        existing_completed_count = (
            existing_completed_count or 0
        )

        if book.status == "paused":
            return {
                "book_id": book_id,
                "skipped": True,
                "reason": "Book is paused",
            }

        if (
            not resume
            and (
                book.stage == "queued_resume"
                or (
                    book.status == "queued"
                    and existing_completed_count > 0
                )
            )
        ):
            return {
                "book_id": book_id,
                "skipped": True,
                "reason": (
                    "Stale generation job"
                ),
            }

    ctx["active_book_id"] = book_id
    executor: ThreadPoolExecutor = (
        ctx["executor"]
    )

    provider = ctx["tts_provider"]

    loop = asyncio.get_running_loop()

    book_directory = Path(
        pdf_path
    ).parent

    try:
        # --------------------------------------------------------------
        # Extract and prepare the book
        # --------------------------------------------------------------

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

        if resume:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Chapter).where(
                        Chapter.book_id == book_id
                    )
                )

                existing_chapters = result.scalars().all()

            pending_keys = {
                (
                    chapter.chapter_number,
                    chapter.title,
                )
                for chapter in existing_chapters
                if chapter.status == "pending"
            }

            chapters = [
                chapter
                for chapter in chapters
                if (
                    chapter.number,
                    chapter.title,
                ) in pending_keys
            ]
        else:
            await create_chapter_records(
                book_id,
                chapters
            )

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

        # --------------------------------------------------------------
        # Calculate total chunks
        # --------------------------------------------------------------

        total_chunks = sum(
            len(
                chunks[
                    chapter.display_title
                ]
            )
            for chapter in chapters
        )

        completed_chunks = 0

        chapter_audio = []

        # --------------------------------------------------------------
        # Generate one chapter at a time
        # --------------------------------------------------------------

        for chapter_position, chapter in enumerate(
            chapters,
            start=1,
        ):
            chapter_chunks = chunks[
                chapter.display_title
            ]

            chunk_paths: list[Path] = []

            for chunk in chapter_chunks:
                # ------------------------------------------------------
                # Temporary chunk directory
                # ------------------------------------------------------

                chapter_directory_name = (
                    (
                        f"chapter_{chapter.number:02d}"
                    )
                    if chapter.number is not None
                    else "extra_chapter"
                )

                chunk_directory = (
                    book_directory
                    / "_work"
                    / chapter_directory_name
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

                # ------------------------------------------------------
                # Generate Kokoro audio
                # ------------------------------------------------------

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
                            / max(
                                total_chunks,
                                1,
                            )
                        )
                        * 65
                    )
                )

                message = (
                    f"Generating Chapter "
                    f"{chapter_position}/"
                    f"{len(chapters)}: "
                    f"{chapter.title} "
                    f"(chunk "
                    f"{chunk.index}/"
                    f"{len(chapter_chunks)})"
                )

                await status_store.update(
                    book_id,
                    status="processing",
                    stage="generating_audio",
                    progress=min(
                        generation_progress,
                        80,
                    ),
                    message=message,
                )

                await update_book_record(
                    book_id,
                    status="processing",
                    stage="generating_audio",
                    progress=min(
                        generation_progress,
                        80,
                    ),
                    message=message,
                )

            # ----------------------------------------------------------
            # Assemble this chapter into its own M4A
            # ----------------------------------------------------------

            chapter_result = (
                await loop.run_in_executor(
                    executor,
                    functools.partial(
                        assemble_chapter,
                        chapter=chapter,
                        chunk_paths=chunk_paths,
                        book_directory=book_directory,
                    ),
                )
            )

            chapter_audio.append(
                chapter_result
            )

            # ----------------------------------------------------------
            # Save chapter metadata
            # ----------------------------------------------------------

            await update_chapter_record(
                book_id=book_id,
                title=chapter.title,
                audio_path=str(
                    chapter_result.m4a_path
                ),
                duration_seconds=(
                    chapter_result.duration_seconds
                ),
            )

        # --------------------------------------------------------------
        # Write audiobook manifest
        # --------------------------------------------------------------

        await status_store.update(
            book_id,
            status="processing",
            stage="assembling",
            progress=90,
            message="Writing audiobook manifest",
        )

        await update_book_record(
            book_id,
            status="processing",
            stage="assembling",
            progress=90,
            message="Writing audiobook manifest",
        )

        manifest_path = (
            book_directory
            / "audiobook"
            / "manifest.json"
        )

        if resume and manifest_path.exists():
            with manifest_path.open(
                "r",
                encoding="utf-8",
            ) as manifest_file:
                manifest = json.load(manifest_file)

            existing_chapters = {
                (
                    chapter["number"],
                    chapter["title"],
                ): chapter
                for chapter in manifest.get(
                    "chapters",
                    [],
                )
            }

            for chapter in chapter_audio:
                key = (
                    chapter["number"],
                    chapter["title"],
                )

                existing_chapters[key] = chapter

            manifest["title"] = book_title

            manifest["chapters"] = sorted(
                existing_chapters.values(),
                key=lambda chapter: (
                    chapter["number"] is None,
                    (
                        chapter["number"]
                        if chapter["number"] is not None
                        else float("inf")
                    ),
                    chapter["title"],
                ),
            )

            with manifest_path.open(
                "w",
                encoding="utf-8",
            ) as manifest_file:
                json.dump(
                    manifest,
                    manifest_file,
                    indent=2,
                )
        else:
            await loop.run_in_executor(
                executor,
                functools.partial(
                    write_manifest,
                    output_directory=(
                        book_directory
                        / "audiobook"
                    ),
                    book_title=book_title,
                    chapters=chapter_audio,
                ),
            )

        # --------------------------------------------------------------
        # Mark completed
        # --------------------------------------------------------------

        await status_store.update(
            book_id,
            status="completed",
            stage="completed",
            progress=100,
            message=("Audiobook chapters generated"),
        )

        await update_book_record(
            book_id,
            status="completed",
            stage="completed",
            progress=100,
            message=("Audiobook chapters generated"),
        )

        ctx.pop(
            "active_book_id",
            None
        )

        return {
            "book_id": book_id,
            "manifest_path": str(
                manifest_path
            ),
            "chapter_count": len(
                chapters
            ),
            "chunk_count": total_chunks,
        }


    except asyncio.CancelledError:
        await asyncio.shield(
            pause_book_record(
                book_id,
                status_store,
            )
        )

        ctx.pop(
            "active_book_id",
            None,
        )

        raise

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

        ctx.pop(
            "active_book_id",
            None
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

    retry_jobs = False

    keep_result = 60 * 60