from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf


DEFAULT_SAMPLE_RATE = 24_000
DEFAULT_SILENCE_SECONDS = 0.25
DEFAULT_BITRATE = "96k"


class AudioAssemblyError(Exception):
    """Raised when audiobook audio assembly fails."""


@dataclass(frozen=True)
class ChapterAudio:
    number: int | None
    title: str
    wav_path: Path
    m4a_path: Path
    duration_seconds: float

@dataclass(frozen=True)
class M4BChapter:
    number: int | None
    title: str
    m4a_path: Path
    duration_seconds: float

def _require_binary(binary: str) -> str:
    path = shutil.which(binary)

    if path is None:
        raise AudioAssemblyError(
            f"Required binary not found: {binary}"
        )

    return path


def _run_command(
    command: list[str],
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()

        raise AudioAssemblyError(
            f"Command failed:\n"
            f"{' '.join(command)}\n\n"
            f"{stderr}"
        ) from exc


def get_audio_duration(
    audio_path: Path,
) -> float:
    """
    Read duration of a WAV/audio file using soundfile.
    """
    info = sf.info(audio_path)

    if info.samplerate <= 0:
        raise AudioAssemblyError(
            f"Invalid sample rate: {audio_path}"
        )

    return info.frames / info.samplerate


def concatenate_wav_files(
    input_paths: list[Path],
    output_path: Path,
    silence_seconds: float = DEFAULT_SILENCE_SECONDS,
) -> Path:
    """
    Concatenate WAV files while inserting a small silence
    between TTS chunks.

    All input files must have the same sample rate and
    channel count.
    """
    if not input_paths:
        raise AudioAssemblyError(
            "No WAV files were supplied."
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    first_info = sf.info(input_paths[0])

    sample_rate = first_info.samplerate
    channels = first_info.channels

    if sample_rate <= 0:
        raise AudioAssemblyError(
            f"Invalid sample rate in {input_paths[0]}"
        )

    silence_frames = int(
        sample_rate * silence_seconds
    )

    silence = np.zeros(
        (silence_frames, channels),
        dtype=np.float32,
    )

    with sf.SoundFile(
        output_path,
        mode="w",
        samplerate=sample_rate,
        channels=channels,
        subtype="PCM_16",
    ) as output:

        for index, input_path in enumerate(input_paths):
            info = sf.info(input_path)

            if info.samplerate != sample_rate:
                raise AudioAssemblyError(
                    "Sample-rate mismatch: "
                    f"{input_path} uses "
                    f"{info.samplerate} Hz, expected "
                    f"{sample_rate} Hz."
                )

            if info.channels != channels:
                raise AudioAssemblyError(
                    "Channel-count mismatch: "
                    f"{input_path} uses "
                    f"{info.channels} channels, expected "
                    f"{channels}."
                )

            audio, _ = sf.read(
                input_path,
                dtype="float32",
                always_2d=True,
            )

            output.write(audio)

            if index < len(input_paths) - 1:
                output.write(silence)

    return output_path


def encode_m4a(
    wav_path: Path,
    output_path: Path,
    bitrate: str = DEFAULT_BITRATE,
) -> Path:
    """
    Encode a chapter WAV into AAC inside an M4A container.
    """
    ffmpeg = _require_binary("ffmpeg")

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(wav_path),
        "-c:a",
        "aac",
        "-b:a",
        bitrate,
        "-ar",
        str(DEFAULT_SAMPLE_RATE),
        "-ac",
        "1",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    _run_command(command)

    return output_path


def _get_encoded_duration(
    audio_path: Path,
) -> float:
    ffprobe = _require_binary("ffprobe")

    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]

    result = _run_command(command)

    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise AudioAssemblyError(
            f"Could not determine duration of "
            f"{audio_path}"
        ) from exc


def _escape_ffmetadata(value: str) -> str:
    """
    Escape characters meaningful to FFmpeg's
    FFMETADATA format.
    """
    return (
        value
        .replace("\\", "\\\\")
        .replace("=", "\\=")
        .replace(";", "\\;")
        .replace("#", "\\#")
        .replace("\n", "\\n")
    )


def create_ffmetadata(
    output_path: Path,
    book_title: str,
    chapters: list[ChapterAudio | M4BChapter],
    author: str | None = None,
) -> Path:
    """
    Create FFmpeg metadata containing audiobook chapter markers.
    """
    lines = [
        ";FFMETADATA1",
        f"title={_escape_ffmetadata(book_title)}",
        "genre=Audiobook",
    ]

    if author:
        lines.append(
            f"artist={_escape_ffmetadata(author)}"
        )

    current_start_ms = 0

    for chapter in chapters:
        duration_ms = round(
            chapter.duration_seconds * 1000
        )

        current_end_ms = (
            current_start_ms + duration_ms
        )

        lines.extend(
            [
                "",
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={current_start_ms}",
                f"END={current_end_ms}",
                (
                    "title="
                    + _escape_ffmetadata(
                        chapter.title
                    )
                ),
            ]
        )

        current_start_ms = current_end_ms

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    return output_path


def create_concat_file(
    output_path: Path,
    audio_paths: list[Path],
) -> Path:
    """
    Create an FFmpeg concat-demuxer file.
    """
    lines = []

    for path in audio_paths:
        escaped = str(
            path.resolve()
        ).replace("'", "'\\''")

        lines.append(
            f"file '{escaped}'"
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    return output_path


def assemble_m4b(
    chapters: list[ChapterAudio | M4BChapter],
    output_path: Path,
    book_title: str,
    author: str | None = None,
) -> Path:
    """
    Concatenate chapter M4A files and create a
    chapter-aware M4B audiobook.
    """
    if not chapters:
        raise AudioAssemblyError(
            "No chapter audio files were supplied."
        )

    ffmpeg = _require_binary("ffmpeg")

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    working_directory = (
        output_path.parent / "_assembly"
    )

    working_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    concat_path = create_concat_file(
        working_directory / "chapters.txt",
        [
            chapter.m4a_path
            for chapter in chapters
        ],
    )

    metadata_path = create_ffmetadata(
        working_directory / "metadata.txt",
        book_title=book_title,
        chapters=chapters,
        author=author,
    )

    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_path),
        "-f",
        "ffmetadata",
        "-i",
        str(metadata_path),
        "-map",
        "0:a:0",
        "-map_metadata",
        "1",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    _run_command(command)

    return output_path