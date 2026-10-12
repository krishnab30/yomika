from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.app.services.audio_assembler import (
    ChapterAudio,
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

from backend.app.services.file_naming import (
    chapter_filename,
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
    chapter,
    chunk_paths: list[Path],
    book_directory: Path,
) -> ChapterAudio:
    """
    Combine one chapter's TTS chunks into a single M4A.
    Intermediate WAV files are removed after successful encoding.
    """
    audiobook_directory = (
        book_directory / "audiobook"
    )

    audiobook_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    work_directory = (
        book_directory
        / "_work"
        / (
            f"chapter_{chapter.number:02d}"
            if chapter.number is not None
            else "extra_chapter"
        )
    )

    work_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    chapter_wav = (
        work_directory / "chapter.wav"
    )

    concatenate_wav_files(
        input_paths=chunk_paths,
        output_path=chapter_wav,
    )

    filename = chapter_filename(
        number=chapter.number,
        title=chapter.title,
    )

    chapter_m4a = (
        audiobook_directory / filename
    )

    encode_m4a(
        wav_path=chapter_wav,
        output_path=chapter_m4a,
    )

    duration = get_audio_duration(
        chapter_wav,
    )

    # The M4A is our durable artifact.
    # WAV is only an intermediate.
    chapter_wav.unlink(
        missing_ok=True
    )

    for chunk_path in chunk_paths:
        chunk_path.unlink(
            missing_ok=True
        )

    return ChapterAudio(
        number=chapter.number,
        title=chapter.display_title,
        wav_path=chapter_wav,
        m4a_path=chapter_m4a,
        duration_seconds=duration,
    )


# deprecated, delete later
# def assemble_book(
#     *,
#     chapters: list[ChapterAudio],
#     book_directory: Path,
#     book_title: str,
# ) -> Path:
#     """
#     Build the final M4B audiobook.
#     """
#     output_path = (
#         book_directory
#         / "audiobook.m4b"
#     )

#     return assemble_m4b(
#         chapters=chapters,
#         output_path=output_path,
#         book_title=book_title,
#     )
