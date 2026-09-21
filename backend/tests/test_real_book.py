from pathlib import Path

from backend.app.services.chapter_parser import parse_chapters
from backend.app.services.text_chunker import chunk_chapters


NORMALIZED_PATH = Path("/Users/krishna/Projects/audiobook-ai/storage/books/c86d5ff9-7099-4fad-8b4c-a115c6865e0b/normalized.txt")


def test_real_book_structure() -> None:
    text = NORMALIZED_PATH.read_text(
        encoding="utf-8"
    )

    chapters = parse_chapters(text)

    assert len(chapters) == 12

    chunks = chunk_chapters(chapters)

    assert len(chunks) == 12

    total_chunks = sum(
        len(chapter_chunks)
        for chapter_chunks in chunks.values()
    )

    assert total_chunks > 100

    for chapter_chunks in chunks.values():
        for chunk in chapter_chunks:
            assert chunk.text.strip()
            assert chunk.character_count > 0