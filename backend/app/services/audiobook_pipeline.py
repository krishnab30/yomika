from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.app.services.audio_assembler import (
    ChapterAudio,
    assemble_m4b,
    concatenate_wav_files,
    encode_m4a,
    get_audio_duration,
)
from backend.app.services.chapter_parser import (
    Chapter,
    parse_chapters,
)
from backend.app.services.pdf_extractor import (
    extract_text,
)
from backend.app.services.text_chunker import (
    TextChunk,
    chunk_chapters,
)
from backend.app.services.text_normalizer import (
    normalize_pdf,
)
from backend.app.services.tts_provider import (
    TTSProvider,
)


@dataclass(frozen=True)
class PreparedBook:
    normalized_path: Path
    chapters: list[Chapter]
    chunks: dict[str, list[TextChunk]]


def prepare_book(
    pdf_path: Path,
    book_directory: Path,
) -> PreparedBook:
    """
    Extract, normalize, parse, and chunk a book.

    This function does not generate audio.
    """
    raw_path = book_directory / "raw.txt"
    normalized_path = (
        book_directory / "normalized.txt"
    )

    extract_text(
        pdf_path=pdf_path,
        output_path=raw_path,
    )

    normalize_pdf(
        pdf_path=pdf_path,
        output_path=normalized_path,
    )

    normalized_text = (
        normalized_path.read_text(
            encoding="utf-8"
        )
    )

    chapters = parse_chapters(
        normalized_text
    )

    chunks = chunk_chapters(
        chapters
    )

    return PreparedBook(
        normalized_path=normalized_path,
        chapters=chapters,
        chunks=chunks,
    )


def generate_chunk_audio(
    *,
    provider: TTSProvider,
    chunk: TextChunk,
    output_path: Path,
    voice: str,
) -> Path:
    """
    Generate one TTS chunk.
    """
    return provider.synthesize(
        text=chunk.text,
        output_path=output_path,
        voice=voice,
    )


def assemble_chapter(
    *,
    chapter: Chapter,
    chunks: list[TextChunk],
    chunk_paths: list[Path],
    book_directory: Path,
) -> ChapterAudio:
    """
    Combine TTS chunks into a chapter and encode it.
    """
    chapter_number = (
        chapter.number
        if chapter.number is not None
        else 999
    )

    chapter_directory = (
        book_directory
        / "audio"
        / f"chapter_{chapter_number:02d}"
    )

    chapter_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    chapter_wav = (
        chapter_directory
        / "chapter.wav"
    )

    concatenate_wav_files(
        input_paths=chunk_paths,
        output_path=chapter_wav,
    )

    chapter_m4a = (
        chapter_directory
        / "chapter.m4a"
    )

    encode_m4a(
        wav_path=chapter_wav,
        output_path=chapter_m4a,
    )

    duration = get_audio_duration(
        chapter_wav
    )

    return ChapterAudio(
        title=chapter.display_title,
        wav_path=chapter_wav,
        m4a_path=chapter_m4a,
        duration_seconds=duration,
    )


def assemble_book(
    *,
    chapters: list[ChapterAudio],
    book_directory: Path,
    book_title: str,
) -> Path:
    """
    Build the final M4B audiobook.
    """
    output_path = (
        book_directory
        / "audiobook.m4b"
    )

    return assemble_m4b(
        chapters=chapters,
        output_path=output_path,
        book_title=book_title,
    )