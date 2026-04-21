"""
Milestone 4 throwaway test: hotkey controls recording.
Hold hotkey to record, release to stop and transcribe. Result printed; no clipboard.
Run from project root: python scripts/test_hotkey_record.py
"""
import os
import sys
import threading
import time

_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
sys.path.insert(0, os.path.join(_project_root, "private_dictate"))

import config
from hotkey import HotkeyListener
from recorder import Recorder
from transcriber import Transcriber


def main() -> None:
    print("Loading model...")
    transcriber = Transcriber(config.MODEL_SIZE, config.DEVICE, config.COMPUTE_TYPE)
    rec = Recorder()
    is_recording = False

    def on_press() -> None:
        nonlocal is_recording
        is_recording = True
        rec.start_recording()
        print("Recording...")

    def on_release() -> None:
        nonlocal is_recording
        if not is_recording:
            return
        is_recording = False
        audio = rec.stop_recording()
        if audio is None:
            print("No audio captured")
            return

        def do_transcribe() -> None:
            print("Transcribing...")
            t0 = time.perf_counter()
            text = transcriber.transcribe(audio)
            elapsed = time.perf_counter() - t0
            if text:
                print(f"Result: {text}")
                print(f"  ({elapsed:.2f}s)")
            else:
                print("Nothing transcribed")

        threading.Thread(target=do_transcribe, daemon=True).start()

    listener = HotkeyListener(config.HOTKEY, on_press, on_release)
    listener.start()
    print(f"Hold [{config.HOTKEY}] to record, release to transcribe. Ctrl+C to quit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        listener.stop()
        print("Done.")


if __name__ == "__main__":
    main()
