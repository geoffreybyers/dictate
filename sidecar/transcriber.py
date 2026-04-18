"""faster-whisper model loading and transcription. Uses settings for language/vad."""

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

from settings import SAMPLE_RATE  # noqa: I001


@dataclass
class TranscriptionResult:
    """Result of a single transcription with optional diagnostics."""

    text: str
    duration_ms: int
    confidence: Optional[float]  # 0-1, from model avg_logprob
    detected_language: Optional[str]


class Transcriber:
    """Loads the faster-whisper model once and exposes transcribe(audio)."""

    def __init__(
        self,
        model_size: str,
        device: str,
        compute_type: str,
        language: Optional[str] = "en",
        vad_filter: bool = True,
    ) -> None:
        self._model = WhisperModel(
            model_size, device=device, compute_type=compute_type
        )
        self._language = language
        self._vad_filter = vad_filter
        # Warm-up with 1s silence
        silence = np.zeros(SAMPLE_RATE, dtype=np.float32)
        self.transcribe(silence)

    def transcribe(self, audio: np.ndarray) -> Optional[TranscriptionResult]:
        """Transcribe audio. Returns None if result is empty after stripping."""
        segments, info = self._model.transcribe(
            audio,
            language=self._language,
            vad_filter=self._vad_filter,
        )
        segment_list = list(segments)
        text = " ".join(s.text.strip() for s in segment_list).strip()
        if not text:
            return None

        duration_ms = int(len(audio) / SAMPLE_RATE * 1000)
        detected_language: Optional[str] = getattr(info, "language", None) if info else None

        confidence: Optional[float] = None
        if segment_list:
            logprobs = [getattr(s, "avg_logprob", None) for s in segment_list]
            valid = [x for x in logprobs if x is not None]
            if valid:
                mean_logprob = sum(valid) / len(valid)
                # avg_logprob is negative; convert to 0-1 confidence
                confidence = max(0.0, min(1.0, math.exp(mean_logprob)))

        return TranscriptionResult(
            text=text,
            duration_ms=duration_ms,
            confidence=confidence,
            detected_language=detected_language,
        )
