from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from arq import ArqRedis
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import Book, Chapter
from backend.app.schemas import (
    BookCreatedResponse,
    BookResponse,
    BookStatusResponse,
    ChapterResponse,
)
from backend.app.services.job_status import JobStatusStore


router = APIRouter(
    prefix="/books",
    tags=["books"],
)


STORAGE_ROOT = Path(
    "storage/books"
)


@router.post(
    "",
    response_model=BookCreatedResponse,
)
async def upload_book(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> BookCreatedResponse:
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A filename is required.",
        )

    if not file.filename.lower().endswith(
        ".pdf"
    ):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    book_id = str(uuid4())

    title = Path(
        file.filename
    ).stem

    book_directory = (
        STORAGE_ROOT / book_id
    )

    book_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    pdf_path = (
        book_directory
        / "original.pdf"
    )

    try:
        with pdf_path.open(
            "wb"
        ) as destination:
            while chunk := await file.read(
                1024 * 1024
            ):
                destination.write(chunk)
    finally:
        await file.close()

    book = Book(
        id=book_id,
        title=title,
        original_filename=file.filename,
        original_path=str(
            pdf_path
        ),
        status="queued",
        stage="queued",
        progress=0,
        message="Queued for processing",
    )

    db.add(book)

    await db.commit()

    status_redis = (
        request.app.state.status_redis
    )

    status_store = JobStatusStore(
        status_redis
    )

    await status_store.update(
        book_id,
        status="queued",
        stage="queued",
        progress=0,
        message="Queued for processing",
    )

    arq: ArqRedis = (
        request.app.state.arq_pool
    )

    await arq.enqueue_job(
        "process_book",
        book_id,
        str(pdf_path),
        title,
        1,
        _job_id=book_id,
    )

    return BookCreatedResponse(
        book_id=book_id,
        title=title,
        status="queued",
    )


@router.post(
    "/{book_id}/continue",
    response_model=BookCreatedResponse,
)
async def continue_book(
    book_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> BookCreatedResponse:
    result = await db.execute(
        select(Book).where(
            Book.id == book_id
        )
    )

    book = result.scalar_one_or_none()

    if book is None:
        raise HTTPException(
            status_code=404,
            detail="Book not found.",
        )

    if book.status in {
        "queued",
        "processing",
    }:
        raise HTTPException(
            status_code=409,
            detail="This book is already being processed.",
        )

    chapter_result = await db.execute(
        select(Chapter).where(
            Chapter.book_id == book_id
        )
    )

    chapters = chapter_result.scalars().all()

    pending_count = sum(
        1
        for chapter in chapters
        if chapter.status == "pending"
    )

    if pending_count == 0:
        raise HTTPException(
            status_code=409,
            detail="This book has no pending chapters.",
        )

    if book.status not in {
        "paused",
        "completed",
        "failed",
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "This book cannot be continued "
                f"from its current state: {book.status}."
            ),
        )

    book.status = "queued"
    book.stage = "queued_resume"
    book.progress = 0
    book.message = (
        f"Queued {pending_count} pending "
        "chapters for generation"
    )

    await db.commit()

    status_redis = (
        request.app.state.status_redis
    )

    status_store = JobStatusStore(
        status_redis
    )

    await status_store.update(
        book_id,
        status="queued",
        stage="queued_resume",
        progress=0,
        message=(
            f"Queued {pending_count} pending "
            "chapters for generation"
        ),
    )

    arq: ArqRedis = (
        request.app.state.arq_pool
    )

    await arq.enqueue_job(
        "process_book",
        book_id,
        book.original_path,
        book.title,
        None,
        True,
        _job_id=(
            f"{book_id}-resume-{uuid4()}"
        ),
    )

    return BookCreatedResponse(
        book_id=book_id,
        title=book.title,
        status="queued",
    )

@router.get(
    "",
    response_model=list[BookResponse],
)
async def list_books(
    db: AsyncSession = Depends(get_db),
) -> list[BookResponse]:
    result = await db.execute(
        select(Book).order_by(
            Book.created_at.desc()
        )
    )

    chapter_result = await db.execute(
        select(
            Chapter.book_id,
            Chapter.status,
        )
    )

    chapter_counts: dict[str, dict[str, int]] = {}

    for row in chapter_result:
        counts = chapter_counts.setdefault(
            row.book_id,
            {
                "completed": 0,
                "pending": 0,
            },
        )

        status = row.status

        if hasattr(status, "value"):
            status = status.value

        if status == "completed":
            counts["completed"] += 1
        elif status == "pending":
            counts["pending"] += 1

    # print("DEBUG chapter_counts:", chapter_counts)

    books = result.scalars().all()

    responses = []

    for book in books:
        response =  BookResponse.model_validate(book)

        counts = chapter_counts.get(
            book.id,
            {
                "completed": 0,
                "pending": 0,
            },
        )

        response.completed_chapter_count = (
            counts["completed"]
        )

        response.pending_chapter_count = (
            counts["pending"]
        )

        responses.append(response)
    
    return responses


@router.get(
    "/{book_id}",
    response_model=BookResponse,
)
async def get_book(
    book_id: str,
    db: AsyncSession = Depends(get_db),
) -> Book:
    result = await db.execute(
        select(Book).where(
            Book.id == book_id
        )
    )

    book = result.scalar_one_or_none()

    if book is None:
        raise HTTPException(
            status_code=404,
            detail="Book not found.",
        )

    return book


@router.get(
    "/{book_id}/status",
    response_model=BookStatusResponse,
)
async def get_book_status(
    book_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> BookStatusResponse:
    result = await db.execute(
        select(Book).where(
            Book.id == book_id
        )
    )

    book = result.scalar_one_or_none()

    if book is None:
        raise HTTPException(
            status_code=404,
            detail="Book not found.",
        )

    status_store = JobStatusStore(
        request.app.state.status_redis
    )

    live_state = await status_store.get(
        book_id
    )

    if live_state is not None:
        return BookStatusResponse(
            book_id=book_id,
            status=live_state.status,
            stage=live_state.stage,
            progress=live_state.progress,
            message=live_state.message,
            updated_at=live_state.updated_at,
        )

    return BookStatusResponse(
        book_id=book_id,
        status=book.status,
        stage=book.stage,
        progress=book.progress,
        message=book.message,
        updated_at=book.updated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Chapter endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{book_id}/chapters",
    response_model=list[ChapterResponse],
)
async def list_chapters(
    book_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[Chapter]:
    book_result = await db.execute(
        select(Book).where(
            Book.id == book_id
        )
    )

    book = book_result.scalar_one_or_none()

    if book is None:
        raise HTTPException(
            status_code=404,
            detail="Book not found.",
        )

    result = await db.execute(
        select(Chapter)
        .where(
            Chapter.book_id == book_id
        )
        .order_by(
            Chapter.chapter_number.is_(None),
            Chapter.chapter_number,
            Chapter.id,
        )
    )

    return list(
        result.scalars().all()
    )


@router.get(
    "/{book_id}/chapters/{chapter_id}",
    response_model=ChapterResponse,
)
async def get_chapter(
    book_id: str,
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
) -> Chapter:
    result = await db.execute(
        select(Chapter).where(
            Chapter.id == chapter_id,
            Chapter.book_id == book_id,
        )
    )

    chapter = result.scalar_one_or_none()

    if chapter is None:
        raise HTTPException(
            status_code=404,
            detail="Chapter not found.",
        )

    return chapter


@router.get(
    "/{book_id}/chapters/{chapter_id}/audio",
)
async def get_chapter_audio(
    book_id: str,
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    result = await db.execute(
        select(Chapter).where(
            Chapter.id == chapter_id,
            Chapter.book_id == book_id,
        )
    )

    chapter = result.scalar_one_or_none()

    if chapter is None:
        raise HTTPException(
            status_code=404,
            detail="Chapter not found.",
        )

    if chapter.status != "completed":
        raise HTTPException(
            status_code=409,
            detail=(
                "Chapter audio is not ready yet."
            ),
        )

    if not chapter.audio_path:
        raise HTTPException(
            status_code=404,
            detail=(
                "Chapter audio file not found."
            ),
        )

    audio_path = Path(
        chapter.audio_path
    )

    if not audio_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Chapter audio file no longer exists."
            ),
        )

    return FileResponse(
        path=audio_path,
        media_type="audio/mp4",
        filename=(
            chapter.filename
            or audio_path.name
        ),
    )


# ---------------------------------------------------------------------------
# Legacy book-level audio endpoint
#
# Kept temporarily while the frontend is migrated to chapter-level audio.
# ---------------------------------------------------------------------------


@router.get(
    "/{book_id}/audio",
)
async def get_book_audio(
    book_id: str,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    result = await db.execute(
        select(Book).where(
            Book.id == book_id
        )
    )

    book = result.scalar_one_or_none()

    if book is None:
        raise HTTPException(
            status_code=404,
            detail="Book not found.",
        )

    if book.status != "completed":
        raise HTTPException(
            status_code=409,
            detail=(
                "Audiobook is not ready yet."
            ),
        )

    if not book.audiobook_path:
        raise HTTPException(
            status_code=404,
            detail=(
                "Audiobook file not found."
            ),
        )

    audio_path = Path(
        book.audiobook_path
    )

    if not audio_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Audiobook file no longer exists."
            ),
        )

    return FileResponse(
        path=audio_path,
        media_type="audio/mp4",
        filename=(
            f"{book.title}.m4b"
        ),
    )