from pathlib import Path

from backend.app.services.chapter_parser import parse_chapters
from backend.app.services.text_chunker import chunk_chapters


NORMALIZED_PATH = Path("/Users/krishna/Projects/audiobook-ai/storage/books/c86d5ff9-7099-4fad-8b4c-a115c6865e0b/normalized.txt")


def main() -> None:
    text = NORMALIZED_PATH.read_text(
        encoding="utf-8"
    )

    chapters = parse_chapters(text)
    chunks = chunk_chapters(chapters)

    for chapter_title, chapter_chunks in chunks.items():
        print()
        print("=" * 80)
        print(chapter_title)
        print("=" * 80)

        for chunk in chapter_chunks[:3]:
            print()
            print(
                f"Chunk {chunk.index} | "
                f"{chunk.character_count} chars | "
                f"{chunk.word_count} words"
            )
            print("-" * 80)
            print(chunk.text[:500])


if __name__ == "__main__":
    main()