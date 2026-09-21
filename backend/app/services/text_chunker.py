from __future__ import annotations

import re
from dataclasses import dataclass

from backend.app.services.chapter_parser import Chapter


DEFAULT_TARGET_CHARACTERS = 750
DEFAULT_MAX_CHARACTERS = 1000


@dataclass(frozen=True)
class TextChunk:
    chapter_number: int | None
    chapter_title: str
    index: int
    text: str

    @property
    def character_count(self) -> int:
        return len(self.text)

    @property
    def word_count(self) -> int:
        return len(self.text.split())


def split_into_sentences(
    paragraph: str,
) -> list[str]:
    """
    Lightweight sentence splitter suitable for our MVP.

    Most paragraphs will never need this. It is primarily used
    when a single paragraph is too large for one TTS chunk.
    """
    sentence_pattern = re.compile(
        r".+?(?:[.!?…]+['\"”’]?(?=\s|$)|$)",
        re.DOTALL,
    )

    sentences = [
        match.group(0).strip()
        for match in sentence_pattern.finditer(
            paragraph
        )
    ]

    return [
        sentence
        for sentence in sentences
        if sentence
    ]


def split_long_sentence(
    sentence: str,
    max_characters: int,
) -> list[str]:
    """
    Last-resort splitting for an unusually long sentence.

    We split on word boundaries rather than cutting through words.
    """
    words = sentence.split()

    parts: list[str] = []
    current: list[str] = []
    current_length = 0

    for word in words:
        additional_length = len(word)

        if current:
            additional_length += 1

        if (
            current
            and current_length + additional_length
            > max_characters
        ):
            parts.append(" ".join(current))
            current = [word]
            current_length = len(word)
        else:
            current.append(word)
            current_length += additional_length

    if current:
        parts.append(" ".join(current))

    return parts


def split_paragraph(
    paragraph: str,
    target_characters: int,
    max_characters: int,
) -> list[str]:
    """
    Split one paragraph into TTS-friendly pieces.
    """
    if len(paragraph) <= max_characters:
        return [paragraph]

    sentences = split_into_sentences(paragraph)

    if not sentences:
        return split_long_sentence(
            paragraph,
            max_characters,
        )

    normalized_sentences: list[str] = []

    for sentence in sentences:
        if len(sentence) <= max_characters:
            normalized_sentences.append(sentence)
        else:
            normalized_sentences.extend(
                split_long_sentence(
                    sentence,
                    max_characters,
                )
            )

    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for sentence in normalized_sentences:
        additional_length = len(sentence)

        if current:
            additional_length += 1

        if (
            current
            and current_length + additional_length
            > target_characters
        ):
            chunks.append(" ".join(current))
            current = [sentence]
            current_length = len(sentence)
        else:
            current.append(sentence)
            current_length += additional_length

    if current:
        chunks.append(" ".join(current))

    return chunks


def chunk_chapter(
    chapter: Chapter,
    target_characters: int = DEFAULT_TARGET_CHARACTERS,
    max_characters: int = DEFAULT_MAX_CHARACTERS,
) -> list[TextChunk]:
    """
    Convert a chapter into naturally bounded TTS chunks.

    Paragraph boundaries are preferred. Large paragraphs are split
    at sentence boundaries where possible.
    """
    paragraphs = [
        paragraph.strip()
        for paragraph in chapter.content.split("\n\n")
        if paragraph.strip()
    ]

    chunks: list[TextChunk] = []
    current_parts: list[str] = []
    current_length = 0

    def flush() -> None:
        nonlocal current_parts
        nonlocal current_length

        if not current_parts:
            return

        chunks.append(
            TextChunk(
                chapter_number=chapter.number,
                chapter_title=chapter.title,
                index=len(chunks) + 1,
                text="\n\n".join(current_parts),
            )
        )

        current_parts = []
        current_length = 0

    for paragraph in paragraphs:
        if len(paragraph) > max_characters:
            flush()

            split_parts = split_paragraph(
                paragraph=paragraph,
                target_characters=target_characters,
                max_characters=max_characters,
            )

            for part in split_parts:
                chunks.append(
                    TextChunk(
                        chapter_number=chapter.number,
                        chapter_title=chapter.title,
                        index=len(chunks) + 1,
                        text=part,
                    )
                )

            continue

        additional_length = len(paragraph)

        if current_parts:
            additional_length += 2

        if (
            current_parts
            and current_length + additional_length
            > target_characters
        ):
            flush()

        current_parts.append(paragraph)

        current_length = (
            sum(len(part) for part in current_parts)
            + 2 * (len(current_parts) - 1)
        )

    flush()

    return chunks


def chunk_chapters(
    chapters: list[Chapter],
    target_characters: int = DEFAULT_TARGET_CHARACTERS,
    max_characters: int = DEFAULT_MAX_CHARACTERS,
) -> dict[str, list[TextChunk]]:
    """
    Chunk every chapter independently.
    """
    result: dict[str, list[TextChunk]] = {}

    for chapter in chapters:
        key = chapter.display_title

        result[key] = chunk_chapter(
            chapter=chapter,
            target_characters=target_characters,
            max_characters=max_characters,
        )

    return result