"""Entry point: startup validation, wire components, push-to-talk loop, graceful shutdown."""

import sys
import threading
import time

import ctranslate2

import clipboard
import config
from hotkey import HotkeyListener
from recorder import Recorder
from transcriber import Transcriber


VALID_COMBINATIONS = {
    ("cpu", "int8"),
    ("cuda", "float16"),
    ("cuda", "int8_float16"),
}


def _resolve_device_and_compute() -> tuple[str, str]:
    """Validate and resolve device/compute; fall back to CPU if CUDA unavailable."""
    device = config.DEVICE
    compute_type = config.COMPUTE_TYPE

    if device == "cuda":
        try:
            supported = ctranslate2.get_supported_devices()
            if "cuda" not in supported:
                print("CUDA not available on this system. Falling back to CPU with int8.")
                device, compute_type = "cpu", "int8"
        except Exception as e:
            print(f"Could not detect CUDA: {e}. Falling back to CPU with int8.")
            device, compute_type = "cpu", "int8"

    if (device, compute_type) not in VALID_COMBINATIONS:
        print(
            "Invalid DEVICE/COMPUTE_TYPE combination. Valid: cpu+int8, cuda+float16, cuda+int8_float16."
        )
        sys.exit(1)

    return device, compute_type


def main() -> None:
    device, compute_type = _resolve_device_and_compute()

    print("dictate v1.0")
    print("─────────────────────────────────────")
    print(f"Model:       {config.MODEL_SIZE}")
    print(f"Device:      {device}")
    print(f"Compute:     {compute_type}")
    print(f"Language:    {config.LANGUAGE or 'auto'}")
    print(f"VAD filter:  {'on' if config.VAD_FILTER else 'off'}")
    print(f"Hotkey:      {config.HOTKEY}")
    print("─────────────────────────────────────")
    print("Loading model... (this may take a moment)")

    t0 = time.perf_counter()
    transcriber = Transcriber(config.MODEL_SIZE, device, compute_type)
    load_time = time.perf_counter() - t0
    print(f"✓ Model ready — {load_time:.1f}s")
    print()

    recorder = Recorder()
    transcription_lock = threading.Lock()
    is_recording = False

    def on_press() -> None:
        nonlocal is_recording
        is_recording = True
        recorder.start_recording()
        print("🎙  Recording...")

    def on_release() -> None:
        nonlocal is_recording
        if not is_recording:
            return
        is_recording = False
        audio = recorder.stop_recording()
        if audio is None:
            print("No audio captured")
            print()
            print(f"Hold [{config.HOTKEY}] to record. Ctrl+C to quit.")
            print()
            return
        if not transcription_lock.acquire(blocking=False):
            print("Transcription in progress, skipped.")
            print()
            print(f"Hold [{config.HOTKEY}] to record. Ctrl+C to quit.")
            print()
            return

        def run_transcription() -> None:
            try:
                print("⏳  Transcribing...")
                start = time.time()
                text = transcriber.transcribe(audio)
                elapsed = time.time() - start
                if text:
                    clipboard.copy_to_clipboard(text)
                    print(f"✓  {text}")
                    print(f"   Copied to clipboard — {elapsed:.2f}s")
                else:
                    print("   Nothing transcribed")
            except Exception as e:
                print(f"Transcription error: {e}")
            finally:
                transcription_lock.release()
            print()
            print(f"Hold [{config.HOTKEY}] to record. Ctrl+C to quit.")
            print()

        threading.Thread(target=run_transcription, daemon=True).start()

    listener = HotkeyListener(config.HOTKEY, on_press, on_release)
    listener.start()

    print(f"Hold [{config.HOTKEY}] to record. Ctrl+C to quit.")
    print()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        listener.stop()
        print("Goodbye.")


if __name__ == "__main__":
    main()
