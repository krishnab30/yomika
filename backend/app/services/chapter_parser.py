from __future__ import annotations

import re
from dataclasses import dataclass


CHAPTER_HEADING_RE = re.compile(
    r"^(Chapter\s+\d+|Extra Chapter):\s*(.+)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Chapter:
    number: int | None
    title: str
    content: str

    @property
    def display_title(self) -> str:
        if self.number is None:
            return f"Extra Chapter: {self.title}"

        return f"Chapter {self.number}: {self.title}"


def parse_chapters(text: str) -> list[Chapter]:
    """
    Parse normalized audiobook text into ordered chapters.

    Expected chapter headings look like:

        Chapter 1: Floating Fortress
        Chapter 2: An Audience with Perugius
        Extra Chapter: The Birth of a New Sword King
    """

    lines = text.splitlines()

    chapter_starts: list[tuple[int, int | None, str]] = []

    for index, line in enumerate(lines):
        line = line.strip()

        if not line:
            continue

        match = CHAPTER_HEADING_RE.match(line)

        if not match:
            continue

        label = match.group(1)
        title = match.group(2).strip()

        if label.lower().startswith("chapter"):
            number_match = re.search(r"\d+", label)

            if number_match is None:
                raise ValueError(
                    f"Could not parse chapter number: {label}"
                )

            number = int(number_match.group())
        else:
            number = None

        chapter_starts.append(
            (index, number, title)
        )

    if not chapter_starts:
        raise ValueError(
            "No chapter headings were found in the normalized text."
        )

    chapters: list[Chapter] = []

    for chapter_index, (
        start_line,
        number,
        title,
    ) in enumerate(chapter_starts):

        if chapter_index + 1 < len(chapter_starts):
            end_line = chapter_starts[
                chapter_index + 1
            ][0]
        else:
            end_line = len(lines)

        body = "\n".join(
            lines[start_line + 1:end_line]
        ).strip()

        if not body:
            raise ValueError(
                f"Chapter has no content: "
                f"{number if number is not None else 'Extra'} - {title}"
            )

        chapters.append(
            Chapter(
                number=number,
                title=title,
                content=body,
            )
        )

    return chapters