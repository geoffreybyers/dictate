"""Microphone capture via sounddevice."""

import threading
import numpy as np
import sounddevice as sd

import config


class Recorder:
    """Records audio while recording event is set; returns buffer on stop."""

    def __init__(self) -> None:
        self._sample_rate = config.SAMPLE_RATE
        self._recording = threading.Event()
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()

    def _audio_callback(self, indata: np.ndarray, _frames: int, _time: any, _status: sd.CallbackFlags) -> None:
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
            print(f"Microphone error: {e}")
            print("Available input devices:")
            print(sd.query_devices(kind="input"))
            print("Select a default input device or install a microphone.")

    def stop_recording(self) -> np.ndarray | None:
        self._recording.clear()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        # Read chunks after stream is stopped so callback cannot append anymore
        with self._lock:
            if not self._chunks:
                return None
            buffer = np.concatenate(self._chunks, axis=0)
            # flatten in case shape is (n, 1)
            if buffer.ndim > 1:
                buffer = buffer.flatten()
            self._chunks.clear()
        min_samples = int(0.5 * self._sample_rate)
        if len(buffer) < min_samples:
            return None
        return buffer
