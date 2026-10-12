from pathlib import Path

from backend.app.services.text_normalizer import normalize_pdf


PDF_PATH = Path("/Users/krishna/Projects/audiobook-ai/storage/books/0c1ce0f1-3eb4-455f-906a-f054f9c23b74/original.pdf")
OUTPUT_PATH = Path("/Users/krishna/Projects/audiobook-ai/storage/books/0c1ce0f1-3eb4-455f-906a-f054f9c23b74/normalized.txt")

def test_normalize_real_pdf() -> None:
    stats = normalize_pdf(
        pdf_path=PDF_PATH,
        output_path=OUTPUT_PATH,
    )

    assert OUTPUT_PATH.exists()

    assert stats.chapter_count == 12
    assert stats.selected_page_count == 258
    assert stats.stop_page == 269
    assert stats.paragraph_count > 2000