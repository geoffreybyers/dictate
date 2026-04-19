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


def _cuda_available() -> bool:
    try:
        import ctranslate2
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


class Transcriber:
    def __init__(
        self,
        size: str = "small",
        device: str = "auto",
        compute_type: str = "auto",
        cache_dir: Optional[Path] = None,
    ):
        self.last_error: Optional[str] = None
        if device == "auto":
            device = "cuda" if _cuda_available() else "cpu"
        resolved_compute = _resolve_compute_type(device, compute_type)
        log.info("loading whisper model size=%s device=%s compute_type=%s",
                 size, device, resolved_compute)
        download_root = str(cache_dir) if cache_dir else None
        try:
            self._model = WhisperModel(
                size,
                device=device,
                compute_type=resolved_compute,
                download_root=download_root,
            )
        except Exception as e:
            if device == "cuda":
                msg = f"CUDA init failed, fell back to CPU: {e}"
                log.warning(msg)
                self.last_error = msg
                device = "cpu"
                resolved_compute = _resolve_compute_type(device, compute_type)
                self._model = WhisperModel(
                    size,
                    device=device,
                    compute_type=resolved_compute,
                    download_root=download_root,
                )
            else:
                raise
        self.size = size
        self.device = device
        self.compute_type = resolved_compute

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
