"""
Milestone 1 throwaway test: load model and transcribe a local .wav file.
Run from project root: python scripts/test_transcriber.py [path_to_16khz_mono.wav]
If no path is given, runs warm-up only (transcribe 1s silence twice to show warm-up effect).
"""
import os
import sys
import time
import wave

import numpy as np

# Allow importing from private_dictate/ when run from project root
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
sys.path.insert(0, os.path.join(_project_root, "private_dictate"))

import config
from transcriber import Transcriber


def load_wav(path: str) -> tuple[np.ndarray, int]:
    """Load a .wav file; returns (float32 mono array, sample_rate)."""
    with wave.open(path, "rb") as wav:
        nch = wav.getnchannels()
        sampwidth = wav.getsampwidth()
        framerate = wav.getframerate()
        nframes = wav.getnframes()
        raw = wav.readframes(nframes)
    if nch != 1:
        raise ValueError(f"Expected mono, got {nch} channels")
    if framerate != 16000:
        raise ValueError(f"Expected 16 kHz, got {framerate} Hz. Resample the file.")
    if sampwidth == 2:  # 16-bit
        samples = np.frombuffer(raw, dtype=np.int16)
        audio = samples.astype(np.float32) / 32768.0
    else:
        raise ValueError(f"Unsupported sample width {sampwidth}")
    return audio, framerate


def main() -> None:
    wav_path = sys.argv[1] if len(sys.argv) > 1 else None

    print("Loading Transcriber (model + warm-up if enabled)...")
    t0 = time.perf_counter()
    transcriber = Transcriber(config.MODEL_SIZE, config.DEVICE, config.COMPUTE_TYPE)
    load_time = time.perf_counter() - t0
    print(f"Model ready — {load_time:.2f}s")

    if wav_path:
        print(f"Loading WAV: {wav_path}")
        audio, sr = load_wav(wav_path)
        assert sr == config.SAMPLE_RATE
        print("Transcribing...")
        t1 = time.perf_counter()
        text = transcriber.transcribe(audio)
        elapsed = time.perf_counter() - t1
        print(f"Result ({elapsed:.2f}s): {text!r}")
    else:
        print("No WAV path given. Running warm-up check: transcribe 1s silence twice.")
        silence = np.zeros(config.SAMPLE_RATE, dtype=np.float32)
        t1 = time.perf_counter()
        transcriber.transcribe(silence)
        first = time.perf_counter() - t1
        t2 = time.perf_counter()
        transcriber.transcribe(silence)
        second = time.perf_counter() - t2
        print(f"First (cold): {first:.2f}s, Second (warm): {second:.2f}s")
        print("(First may be slower; warm-up reduces this.)")


if __name__ == "__main__":
    main()
