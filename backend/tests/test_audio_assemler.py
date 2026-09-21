from pathlib import Path

import numpy as np
import soundfile as sf

from backend.app.services.audio_assembler import (
    ChapterAudio,
    assemble_m4b,
    concatenate_wav_files,
    encode_m4a,
    get_audio_duration,
)


SAMPLE_RATE = 24_000


def create_test_wav(
    path: Path,
    duration_seconds: float,
) -> None:
    frames = int(
        SAMPLE_RATE * duration_seconds
    )

    audio = np.zeros(
        frames,
        dtype=np.float32,
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    sf.write(
        path,
        audio,
        SAMPLE_RATE,
    )


def test_concatenate_wavs(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"
    output = tmp_path / "combined.wav"

    create_test_wav(first, 0.5)
    create_test_wav(second, 0.5)

    concatenate_wav_files(
        [first, second],
        output,
        silence_seconds=0.25,
    )

    duration = get_audio_duration(output)

    assert output.exists()

    assert 1.20 < duration < 1.30


def test_encode_m4a(
    tmp_path: Path,
) -> None:
    source = tmp_path / "chapter.wav"
    output = tmp_path / "chapter.m4a"

    create_test_wav(source, 0.5)

    encode_m4a(
        source,
        output,
    )

    assert output.exists()
    assert output.stat().st_size > 0


def test_create_m4b(
    tmp_path: Path,
) -> None:
    wav_one = tmp_path / "chapter1.wav"
    wav_two = tmp_path / "chapter2.wav"

    m4a_one = tmp_path / "chapter1.m4a"
    m4a_two = tmp_path / "chapter2.m4a"

    output = tmp_path / "book.m4b"

    create_test_wav(wav_one, 0.5)
    create_test_wav(wav_two, 0.5)

    encode_m4a(
        wav_one,
        m4a_one,
    )

    encode_m4a(
        wav_two,
        m4a_two,
    )

    chapter_one = ChapterAudio(
        title="Chapter 1: Test",
        wav_path=wav_one,
        m4a_path=m4a_one,
        duration_seconds=0.5,
    )

    chapter_two = ChapterAudio(
        title="Chapter 2: Test",
        wav_path=wav_two,
        m4a_path=m4a_two,
        duration_seconds=0.5,
    )

    assemble_m4b(
        chapters=[
            chapter_one,
            chapter_two,
        ],
        output_path=output,
        book_title="Test Audiobook",
    )

    assert output.exists()
    assert output.stat().st_size > 0