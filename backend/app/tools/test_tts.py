from __future__ import annotations

from pathlib import Path

from backend.app.services.chapter_parser import parse_chapters
from backend.app.services.kokoro_tts import KokoroProvider
from backend.app.services.text_chunker import chunk_chapters


NORMALIZED_PATH = Path("/Users/krishna/Projects/audiobook-ai/storage/books/c86d5ff9-7099-4fad-8b4c-a115c6865e0b/normalized.txt")
OUTPUT_PATH = Path(
    "/Users/krishna/Projects/audiobook-ai/storage/tts_test/chapter1_chunk1.wav"
)


def main() -> None:
    text = NORMALIZED_PATH.read_text(
        encoding="utf-8"
    )

    chapters = parse_chapters(text)

    chunked_chapters = chunk_chapters(
        chapters
    )

    chapter_one = chapters[0]

    chunks = chunked_chapters[
        chapter_one.display_title
    ]

    first_chunk = chunks[0]

    print(
        f"Chapter: {chapter_one.display_title}"
    )

    print(
        f"Chunk: {first_chunk.index}"
    )

    print(
        f"Characters: "
        f"{first_chunk.character_count}"
    )

    print()
    print("Text:")
    print(first_chunk.text)

    print()
    print("Loading Kokoro...")

    provider = KokoroProvider()

    print("Generating audio...")

    output = provider.synthesize(
        text=first_chunk.text,
        output_path=OUTPUT_PATH,
        voice="af_heart",
    )

    print()
    print(f"Audio written to: {output}")


if __name__ == "__main__":
    main()