from pathlib import Path

import pymupdf


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be extracted successfully."""


def extract_text(
    pdf_path: Path,
    output_path: Path,
) -> dict[str, int]:
    """
    Extract raw text from a PDF, preserving page boundaries.

    Returns basic extraction statistics.
    """
    try:
        document = pymupdf.open(pdf_path)
    except Exception as exc:
        raise PDFExtractionError(
            f"Failed to open PDF: {pdf_path.name}"
        ) from exc

    page_sections: list[str] = []
    total_characters = 0

    try:
        page_count = document.page_count

        if page_count == 0:
            raise PDFExtractionError("PDF contains no pages.")

        for page_number in range(page_count):
            page = document[page_number]
            text = page.get_text("text").strip()

            total_characters += len(text)

            page_sections.append(
                f"===== PAGE {page_number + 1} =====\n\n"
                f"{text}\n"
            )

    finally:
        document.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    raw_text = "\n\n".join(page_sections)
    output_path.write_text(raw_text, encoding="utf-8")

    return {
        "page_count": page_count,
        "character_count": total_characters,
    }