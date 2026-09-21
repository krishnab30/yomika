from __future__ import annotations

import os

import torch
from kokoro import KPipeline


os.environ.setdefault(
    "PYTORCH_ENABLE_MPS_FALLBACK",
    "1",
)


def main() -> None:
    print(f"PyTorch: {torch.__version__}")
    print(
        f"MPS available: "
        f"{torch.backends.mps.is_available()}"
    )

    if not torch.backends.mps.is_available():
        raise RuntimeError(
            "MPS is not available on this machine."
        )

    print("Initializing Kokoro...")

    pipeline = KPipeline(
        lang_code="a",
    )

    print("Kokoro initialized successfully.")

    text = (
        "The night was quiet. "
        "The town was asleep, and the moon "
        "hung over the rooftops."
    )

    generator = pipeline(
        text,
        voice="af_heart",
    )

    for index, (graphemes, phonemes, audio) in enumerate(
        generator,
        start=1,
    ):
        print(
            f"Segment {index}: "
            f"{len(graphemes)} graphemes"
        )
        print(
            f"Phonemes: {phonemes[:100]}"
        )

        print(
            f"Audio type: {type(audio)}"
        )

        break


if __name__ == "__main__":
    main()