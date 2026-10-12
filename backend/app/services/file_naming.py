from __future__ import annotations

import re


def sanitize_filename(value: str) -> str:
    value = value.strip()

    value = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.rstrip(". ")

def chapter_filename(
    number: int | None,
    title: str,
) -> str:
    safe_title = sanitize_filename(title)

    if number is None:
        return (
            f"Extra Chapter - "
            f"{safe_title}.m4a"
        )

    return (
        f"{number:02d} - "
        f"{safe_title}.m4a"
    )