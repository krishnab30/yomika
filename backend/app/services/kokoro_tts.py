from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from kokoro import KPipeline

from backend.app.services.tts_provider import TTSProvider


SAMPLE_RATE = 24_000
DEFAULT_LANGUAGE = "a"
DEFAULT_VOICE = "af_heart"


class KokoroProvider(TTSProvider):
    """
    Local Kokoro-82M text-to-speech provider.
    """

    def __init__(
        self,
        language: str = DEFAULT_LANGUAGE,
    ) -> None:
        os.environ.setdefault(
            "PYTORCH_ENABLE_MPS_FALLBACK",
            "1",
        )

        self.language = language

        self.pipeline = KPipeline(
            lang_code=language,
            repo_id="hexgrad/Kokoro-82M",
        )

    @staticmethod
    def _audio_to_numpy(audio: object) -> np.ndarray:
        if isinstance(audio, torch.Tensor):
            return (
                audio.detach()
                .cpu()
                .numpy()
            )

        return np.asarray(audio)

    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str = DEFAULT_VOICE,
    ) -> Path:
        if not text.strip():
            raise ValueError(
                "Cannot synthesize empty text."
            )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        segments: list[np.ndarray] = []

        generator = self.pipeline(
            text,
            voice=voice,
        )

        for _, _, audio in generator:
            if audio is None:
                continue

            segments.append(
                self._audio_to_numpy(audio)
            )

        if not segments:
            raise RuntimeError(
                "Kokoro produced no audio."
            )

        waveform = np.concatenate(
            segments
        )

        sf.write(
            output_path,
            waveform,
            SAMPLE_RATE,
        )

        return output_path