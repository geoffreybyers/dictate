"""faster-whisper model loading and transcription."""

import numpy as np
from faster_whisper import WhisperModel

import config


class Transcriber:
    """Loads the faster-whisper model once and exposes transcribe(audio)."""

    def __init__(
        self,
        model_size: str,
        device: str,
        compute_type: str,
    ) -> None:
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
        if config.WARMUP:
            silence = np.zeros(config.SAMPLE_RATE, dtype=np.float32)
            self.transcribe(silence)

    def transcribe(self, audio: np.ndarray) -> str | None:
        """Transcribe audio to text. Returns None if result is empty after stripping."""
        segments, _ = self._model.transcribe(
            audio,
            language=config.LANGUAGE,
            vad_filter=config.VAD_FILTER,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return text if text else None
