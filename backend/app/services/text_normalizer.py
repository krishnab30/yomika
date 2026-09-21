from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf


CHAPTER_RE = re.compile(
    r"^(Chapter \d+|Extra Chapter):\s*(.*)$",
    re.IGNORECASE,
)

STOP_RE = re.compile(
    r"^(About the Author|Newsletter)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TextLine:
    text: str
    top: float
    bottom: float
    left: float
    page_number: int


@dataclass(frozen=True)
class NormalizationStats:
    source_page_count: int
    selected_page_count: int
    chapter_count: int
    paragraph_count: int
    character_count: int
    stop_page: int | None


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_layout_lines(page: pymupdf.Page) -> list[TextLine]:
    """
    Extract text lines while preserving their page coordinates.

    Coordinates allow us to distinguish normal line wrapping from
    actual paragraph breaks.
    """
    lines: list[TextLine] = []

    data = page.get_text("dict")

    for block in data["blocks"]:
        if block.get("type") != 0:
            continue

        for line in block.get("lines", []):
            text = normalize_whitespace(
                "".join(
                    span.get("text", "")
                    for span in line.get("spans", [])
                )
            )

            if not text:
                continue

            x0, y0, _x1, y1 = line["bbox"]

            lines.append(
                TextLine(
                    text=text,
                    top=y0,
                    bottom=y1,
                    left=x0,
                    page_number=page.number + 1,
                )
            )

    lines.sort(key=lambda item: (item.top, item.left))

    return lines


def median(values: list[float]) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)
    middle = len(ordered) // 2

    if len(ordered) % 2:
        return ordered[middle]

    return (ordered[middle - 1] + ordered[middle]) / 2


def paragraphize(lines: list[TextLine]) -> list[str]:
    """
    Convert visually wrapped lines into logical paragraphs.

    The PDF uses noticeably larger vertical spacing between paragraphs
    than between ordinary text lines.
    """
    if not lines:
        return []

    gaps = [
        max(
            0.0,
            lines[index + 1].top - lines[index].bottom,
        )
        for index in range(len(lines) - 1)
    ]

    typical_gap = median(gaps)

    # The exact threshold is deliberately conservative.
    paragraph_gap = max(8.0, typical_gap * 1.65)

    paragraphs: list[str] = []
    current = lines[0].text

    for previous, current_line in zip(lines, lines[1:]):
        gap = max(
            0.0,
            current_line.top - previous.bottom,
        )

        if gap >= paragraph_gap:
            paragraphs.append(current.strip())
            current = current_line.text
            continue

        # Handle words split across lines by PDF hyphenation.
        if (
            current.endswith("-")
            and current_line.text
            and current_line.text[0].islower()
        ):
            current = current[:-1] + current_line.text
        else:
            current += " " + current_line.text

    paragraphs.append(current.strip())

    return paragraphs


def is_complete_sentence(text: str) -> bool:
    """
    Used when a paragraph continues across a PDF page boundary.
    """
    text = text.rstrip()

    if not text:
        return True

    if re.search(
        r'[.!?…]["”’\']?$',
        text,
    ):
        return True

    if text.endswith(("”", '"')):
        return True

    return False


def merge_page_paragraphs(
    page_paragraphs: list[list[str]],
) -> list[str]:
    """
    Join paragraphs that were split only because the PDF page ended.
    """
    merged: list[str] = []

    for paragraphs in page_paragraphs:
        if not paragraphs:
            continue

        if not merged:
            merged.extend(paragraphs)
            continue

        first = paragraphs[0]
        previous = merged[-1]

        if not is_complete_sentence(previous):
            if (
                previous.endswith("-")
                and first
                and first[0].islower()
            ):
                merged[-1] = previous[:-1] + first
            else:
                merged[-1] = previous + " " + first

            merged.extend(paragraphs[1:])
        else:
            merged.extend(paragraphs)

    return merged


def format_chapter_heading(
    lines: list[TextLine],
    index: int,
) -> tuple[str | None, int]:
    """
    Normalize chapter headings such as:

        Chapter 1:
        Floating Fortress

    into:

        Chapter 1: Floating Fortress
    """
    match = CHAPTER_RE.match(lines[index].text)

    if not match:
        return None, index

    chapter_kind = match.group(1)
    title = match.group(2).strip()

    if title:
        return (
            f"{chapter_kind}: {title}",
            index + 1,
        )

    # The title is on the next text line.
    if index + 1 < len(lines):
        next_text = lines[index + 1].text

        if next_text and not CHAPTER_RE.match(next_text):
            return (
                f"{chapter_kind}: {next_text}",
                index + 2,
            )

    return lines[index].text, index + 1


def find_story_start(
    page_lines: list[list[TextLine]],
) -> int:
    """
    Locate the first real narrative chapter.

    The table-of-contents page contains many chapter headings,
    whereas an actual chapter-start page contains one chapter
    heading followed by substantial text.
    """
    for page_index, lines in enumerate(page_lines):
        heading_count = sum(
            1
            for line in lines
            if CHAPTER_RE.match(line.text)
        )

        if heading_count == 1 and len(lines) >= 4:
            return page_index

    raise ValueError(
        "Could not locate the beginning of the narrative."
    )


def select_story_pages(
    page_lines: list[list[TextLine]],
    start_page: int,
) -> tuple[list[list[TextLine]], int | None]:
    """
    Keep narrative pages until author/back-matter content begins.
    """
    selected: list[list[TextLine]] = []
    stop_page: int | None = None

    for page_index in range(
        start_page,
        len(page_lines),
    ):
        lines = page_lines[page_index]

        if any(STOP_RE.match(line.text) for line in lines):
            stop_page = page_index + 1
            break

        selected.append(lines)

    return selected, stop_page


def normalize_pdf(
    pdf_path: Path,
    output_path: Path,
) -> NormalizationStats:
    """
    Convert a text-based novel PDF into clean audiobook-ready text.
    """
    document = pymupdf.open(pdf_path)

    try:
        page_lines = [
            extract_layout_lines(page)
            for page in document
        ]
    finally:
        document.close()

    start_page = find_story_start(page_lines)

    selected_pages, stop_page = select_story_pages(
        page_lines,
        start_page,
    )

    page_paragraphs: list[list[str]] = []
    chapter_count = 0

    for lines in selected_pages:
        output: list[str] = []
        body_start = 0

        # Chapter headings in this PDF occur at page starts.
        if lines:
            heading, next_index = format_chapter_heading(
                lines,
                0,
            )

            if heading is not None:
                output.append(heading)
                chapter_count += 1
                body_start = next_index

        body = lines[body_start:]

        output.extend(
            paragraphize(body)
        )

        page_paragraphs.append(output)

    paragraphs = merge_page_paragraphs(
        page_paragraphs
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        "\n\n".join(paragraphs) + "\n",
        encoding="utf-8",
    )

    return NormalizationStats(
        source_page_count=len(page_lines),
        selected_page_count=len(selected_pages),
        chapter_count=chapter_count,
        paragraph_count=len(paragraphs),
        character_count=sum(
            len(paragraph)
            for paragraph in paragraphs
        ),
        stop_page=stop_page,
    )