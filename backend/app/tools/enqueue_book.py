from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path
from uuid import uuid4

from arq import create_pool

from backend.app.database import AsyncSessionLocal
from backend.app.models import Book
from backend.app.worker import REDIS_SETTINGS


async def enqueue_book(
    source_pdf: Path,
    chapter_limit: int | None = None,
) -> None:
    if not source_pdf.exists():
        raise FileNotFoundError(
            source_pdf
        )

    if source_pdf.suffix.lower() != ".pdf":
        raise ValueError(
            "Only PDF files are supported."
        )

    # --------------------------------------------------------------
    # Create book ID and storage directory
    # --------------------------------------------------------------

    book_id = str(uuid4())

    book_directory = (
        Path("storage")
        / "books"
        / book_id
    )

    book_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------------
    # Copy original PDF into book storage
    # --------------------------------------------------------------

    pdf_path = (
        book_directory
        / "original.pdf"
    )

    shutil.copy2(
        source_pdf,
        pdf_path,
    )

    # --------------------------------------------------------------
    # Create persistent Book record BEFORE queueing the job
    #
    # This is important because the worker and API both use this
    # database record as the source of truth for the job.
    # --------------------------------------------------------------

    async with AsyncSessionLocal() as session:
        book = Book(
            id=book_id,
            title=source_pdf.stem,
            original_filename=source_pdf.name,
            original_path=str(pdf_path),
            audiobook_path=None,
            status="queued",
            stage="queued",
            progress=0,
            message="Queued for processing",
        )

        session.add(book)

        await session.commit()

    # --------------------------------------------------------------
    # Queue the background job
    # --------------------------------------------------------------

    redis = await create_pool(
        REDIS_SETTINGS
    )

    try:
        job = await redis.enqueue_job(
            "process_book",
            book_id,
            str(pdf_path),
            source_pdf.stem,
            chapter_limit,
            _job_id=book_id,
        )

        if job is None:
            print(
                "A job with this book ID already exists."
            )
            return

        print(
            f"Book ID: {book_id}"
        )

        print(
            f"Job ID: {job.job_id}"
        )

        print(
            "Queued successfully."
        )

    except Exception as exc:
        # ----------------------------------------------------------
        # If Redis enqueue fails after the DB record was created,
        # keep the record but mark it as failed so the API does not
        # show a permanently queued book.
        # ----------------------------------------------------------

        async with AsyncSessionLocal() as session:
            db_book = await session.get(
                Book,
                book_id,
            )

            if db_book is not None:
                db_book.status = "failed"
                db_book.stage = "failed"
                db_book.progress = 0
                db_book.message = (
                    f"Failed to queue job: {exc}"
                )

                await session.commit()

        raise

    finally:
        await redis.aclose()


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: "
            "python -m backend.app.tools.enqueue_book "
            "/path/to/book.pdf "
            "[chapter_limit]"
        )

    pdf_path = Path(
        sys.argv[1]
    ).expanduser()

    chapter_limit = None

    if len(sys.argv) >= 3:
        chapter_limit = int(
            sys.argv[2]
        )

    asyncio.run(
        enqueue_book(
            source_pdf=pdf_path,
            chapter_limit=chapter_limit,
        )
    )


if __name__ == "__main__":
    main()