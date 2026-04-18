"""Microphone capture via sounddevice. Uses sample_rate from settings."""

import threading
from typing import Any, Optional

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000


class Recorder:
    """Records audio while recording event is set; returns buffer on stop."""

    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        self._sample_rate = sample_rate
        self._recording = threading.Event()
        self._chunks: list[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()

    def _audio_callback(
        self,
        indata: np.ndarray,
        _frames: int,
        _time: Any,
        _status: sd.CallbackFlags,
    ) -> None:
        if self._recording.is_set():
            with self._lock:
                self._chunks.append(indata.copy())

    def start_recording(self) -> None:
        self._recording.set()
        with self._lock:
            self._chunks.clear()
        try:
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype=np.float32,
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as e:
            self._recording.clear()
            self._stream = None
            raise RuntimeError(f"Microphone error: {e}") from e

    def stop_recording(self) -> Optional[np.ndarray]:
        self._recording.clear()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if not self._chunks:
                return None
            buffer = np.concatenate(self._chunks, axis=0)
            if buffer.ndim > 1:
                buffer = buffer.flatten()
            self._chunks.clear()
        min_samples = int(0.5 * self._sample_rate)
        if len(buffer) < min_samples:
            return None
        return buffer
