"""Microphone capture via sounddevice. Mono float32 @ 16 kHz."""
from __future__ import annotations

import logging
import threading
from typing import Optional

import numpy as np
import sounddevice as sd

from private_dictate.errors import AudioError

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000


class Recorder:
    def __init__(self, sample_rate: int = SAMPLE_RATE, mic: Optional[str] = None):
        self.sample_rate = sample_rate
        self.mic = mic or None
        self._stream = None
        self._buffers: list[np.ndarray] = []
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._stream is not None:
            return
        self._buffers = []
        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                device=self.mic if self.mic else None,
                callback=self._callback,
            )
            self._stream.start()
        except Exception as e:
            self._stream = None
            raise AudioError(f"microphone start failed: {e}") from e

    def _callback(self, indata, frames, time_info, status):
        if status:
            log.debug("recorder callback status: %s", status)
        with self._lock:
            self._buffers.append(np.array(indata[:, 0], copy=True))

    def stop(self) -> np.ndarray:
        if self._stream is None:
            return np.zeros(0, dtype=np.float32)
        try:
            self._stream.stop()
            self._stream.close()
        except Exception:
            log.exception("recorder stop failed")
        self._stream = None
        with self._lock:
            if not self._buffers:
                return np.zeros(0, dtype=np.float32)
            out = np.concatenate(self._buffers)
            self._buffers = []
            return out
