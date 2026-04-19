"""faster-whisper wrapper. Loads the model once at startup."""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

log = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    text: str
    duration_ms: int
    language: str
    confidence: float


def _resolve_compute_type(device: str, requested: str) -> str:
    if requested != "auto":
        return requested
    return "float16" if device == "cuda" else "int8"


class Transcriber:
    def __init__(
        self,
        size: str = "small",
        device: str = "auto",
        compute_type: str = "auto",
        cache_dir: Optional[Path] = None,
    ):
        if device == "auto":
            try:
                import ctranslate2
                device = "cuda" if "cuda" in ctranslate2.get_supported_devices() else "cpu"
            except Exception:
                device = "cpu"
        compute_type = _resolve_compute_type(device, compute_type)
        log.info("loading whisper model size=%s device=%s compute_type=%s",
                 size, device, compute_type)
        self._model = WhisperModel(
            size,
            device=device,
            compute_type=compute_type,
            download_root=str(cache_dir) if cache_dir else None,
        )
        self.size = size
        self.device = device
        self.compute_type = compute_type

    def transcribe(self, audio: np.ndarray) -> TranscriptionResult:
        if audio.size == 0:
            return TranscriptionResult(text="", duration_ms=0,
                                       language="", confidence=0.0)
        t0 = time.perf_counter()
        segments_iter, info = self._model.transcribe(audio, beam_size=5)
        # Average avg_logprob across segments → confidence in [0, 1]
        texts: list[str] = []
        logprobs: list[float] = []
        for seg in segments_iter:
            texts.append(seg.text.strip())
            logprobs.append(float(getattr(seg, "avg_logprob", -1.0)))
        text = " ".join(t for t in texts if t).strip()
        confidence = float(math.exp(sum(logprobs) / len(logprobs))) if logprobs else 0.0
        confidence = max(0.0, min(1.0, confidence))
        return TranscriptionResult(
            text=text,
            duration_ms=int((time.perf_counter() - t0) * 1000),
            language=getattr(info, "language", ""),
            confidence=confidence,
        )
