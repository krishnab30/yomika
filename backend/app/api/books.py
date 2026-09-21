from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.services.pdf_extractor import (
    PDFExtractionError,
    extract_text,
)
from backend.app.services.text_normalizer import normalize_pdf

router = APIRouter(prefix="/books", tags=["books"])

STORAGE_ROOT = Path("storage/books")


@router.post("")
async def upload_book(
    file: UploadFile = File(...),
) -> dict[str, object]:
    """
    Upload a PDF and extract its raw text.
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A filename is required.",
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    book_id = str(uuid4())

    book_directory = STORAGE_ROOT / book_id
    book_directory.mkdir(parents=True, exist_ok=True)

    pdf_path = book_directory / "original.pdf"
    text_path = book_directory / "raw.txt"

    try:
        with pdf_path.open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                destination.write(chunk)

        extraction_stats = extract_text(
            pdf_path=pdf_path,
            output_path=text_path,
        )

        normalized_path = book_directory / "normalized.txt"

        normalization_stats = normalize_pdf(
            pdf_path=pdf_path,
            output_path=normalized_path,
        )

    except PDFExtractionError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to process the uploaded PDF.",
        ) from exc

    finally:
        await file.close()

    return {
        "book_id": book_id,
        "filename": file.filename,
        "status": "normalized",
        "extraction": extraction_stats,
        "normalization": {
            "source_page_count": (
                normalization_stats.source_page_count
            ),
            "selected_page_count": (
                normalization_stats.selected_page_count
            ),
            "chapter_count": (
                normalization_stats.chapter_count
            ),
            "paragraph_count": (
                normalization_stats.paragraph_count
            ),
            "character_count": (
                normalization_stats.character_count
            ),
            "stop_page": (
                normalization_stats.stop_page
            ),
        },
    }