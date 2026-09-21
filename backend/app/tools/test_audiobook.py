from __future__ import annotations

from pathlib import Path

from backend.app.services.audio_assembler import (
    ChapterAudio,
    assemble_m4b,
    concatenate_wav_files,
    encode_m4a,
    get_audio_duration,
)
from backend.app.services.chapter_parser import parse_chapters
from backend.app.services.kokoro_tts import KokoroProvider
from backend.app.services.text_chunker import chunk_chapters


NORMALIZED_PATH = Path("/Users/krishna/Projects/audiobook-ai/storage/books/c86d5ff9-7099-4fad-8b4c-a115c6865e0b/normalized.txt")

OUTPUT_ROOT = Path(
    "storage/audiobook_test"
)


def main() -> None:
    text = NORMALIZED_PATH.read_text(
        encoding="utf-8",
    )

    chapters = parse_chapters(text)

    chunked = chunk_chapters(
        chapters,
    )

    provider = KokoroProvider()

    chapter_audio: list[ChapterAudio] = []

    # For this development test, generate only the
    # first TTS chunk from the first two chapters.
    for chapter in chapters[:2]:
        chunks = chunked[
            chapter.display_title
        ]

        chunk = chunks[0]

        chunk_directory = (
            OUTPUT_ROOT
            / f"chapter_{chapter.number:02d}"
            / "chunks"
        )

        chunk_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        chunk_path = (
            chunk_directory
            / "chunk_001.wav"
        )

        print(
            f"Generating: "
            f"{chapter.display_title}"
        )

        provider.synthesize(
            text=chunk.text,
            output_path=chunk_path,
            voice="af_heart",
        )

        chapter_directory = (
            OUTPUT_ROOT
            / f"chapter_{chapter.number:02d}"
        )

        chapter_wav = (
            chapter_directory
            / "chapter.wav"
        )

        concatenate_wav_files(
            [chunk_path],
            chapter_wav,
            silence_seconds=0,
        )

        chapter_m4a = (
            chapter_directory
            / "chapter.m4a"
        )

        encode_m4a(
            chapter_wav,
            chapter_m4a,
        )

        duration = get_audio_duration(
            chapter_wav,
        )

        chapter_audio.append(
            ChapterAudio(
                title=chapter.display_title,
                wav_path=chapter_wav,
                m4a_path=chapter_m4a,
                duration_seconds=duration,
            )
        )

    audiobook_path = (
        OUTPUT_ROOT
        / "demo_book.m4b"
    )

    assemble_m4b(
        chapters=chapter_audio,
        output_path=audiobook_path,
        book_title="Mushoku Tensei Volume 14",
    )

    print()
    print(
        f"Audiobook written to:\n"
        f"{audiobook_path}"
    )


if __name__ == "__main__":
    main()