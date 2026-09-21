from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path
from uuid import uuid4

from arq import create_pool

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

    pdf_path = (
        book_directory
        / "original.pdf"
    )

    shutil.copy2(
        source_pdf,
        pdf_path,
    )

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