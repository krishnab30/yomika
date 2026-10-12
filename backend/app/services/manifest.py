from __future__ import annotations

import json
from pathlib import Path

from backend.app.services.audio_assembler import (
    ChapterAudio,
)


def write_manifest(
    *,
    output_directory: Path,
    book_title: str,
    chapters: list[ChapterAudio],
) -> Path:
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest_path = (
        output_directory / "manifest.json"
    )

    payload = {
        "title": book_title,
        "chapters": [
            {
                "number": chapter.number,
                "title": chapter.title,
                "filename": chapter.m4a_path.name,
                "duration_seconds": (
                    chapter.duration_seconds
                ),
            }
            for chapter in chapters
        ],
    }

    manifest_path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return manifest_path