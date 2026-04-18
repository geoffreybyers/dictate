"""
Milestone 3 throwaway test: record 5 seconds, pass buffer to Transcriber, print result.
No hotkey, no clipboard. Run from project root: python scripts/test_record_and_transcribe.py
"""
import os
import sys
import time

_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
sys.path.insert(0, os.path.join(_project_root, "dictate"))

import config
from recorder import Recorder
from transcriber import Transcriber


def main() -> None:
    print("Loading model...")
    transcriber = Transcriber(config.MODEL_SIZE, config.DEVICE, config.COMPUTE_TYPE)
    rec = Recorder()
    print("Recording 5 seconds... (speak into the microphone)")
    rec.start_recording()
    time.sleep(5)
    audio = rec.stop_recording()
    if audio is None:
        print("No audio captured")
        return
    print("Transcribing...")
    t0 = time.perf_counter()
    text = transcriber.transcribe(audio)
    elapsed = time.perf_counter() - t0
    print(f"Result ({elapsed:.2f}s): {text!r}")


if __name__ == "__main__":
    main()
