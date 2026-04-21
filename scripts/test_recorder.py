"""
Milestone 2 throwaway test: record 5 seconds, save to test.wav, then play back.
Run from project root: python scripts/test_recorder.py
"""
import os
import sys
import time
import wave

import numpy as np

_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
sys.path.insert(0, os.path.join(_project_root, "private_dictate"))

import config
from recorder import Recorder


def main() -> None:
    out_path = os.path.join(_project_root, "test.wav")
    rec = Recorder()
    print("Recording 5 seconds... (speak into the microphone)")
    rec.start_recording()
    time.sleep(5)
    audio = rec.stop_recording()
    if audio is None:
        print("No audio captured (buffer too short)")
        return
    print(f"Captured {len(audio) / config.SAMPLE_RATE:.2f} s, {len(audio)} samples")
    # Save as 16-bit WAV
    int16 = (audio * 32767).clip(-32768, 32767).astype(np.int16)
    with wave.open(out_path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(config.SAMPLE_RATE)
        wav.writeframes(int16.tobytes())
    print(f"Saved to {out_path}. Play it to confirm 16 kHz mono.")


if __name__ == "__main__":
    main()
