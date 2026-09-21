from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TTSProvider(ABC):
    """
    Abstract interface for text-to-speech engines.

    The rest of the application should depend on this interface,
    not directly on Kokoro.
    """

    @abstractmethod
    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str,
    ) -> Path:
        """
        Convert text into an audio file.
        """
        raise NotImplementedError