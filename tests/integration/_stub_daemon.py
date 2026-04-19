"""Run Daemon with hardware components stubbed — used by integration tests."""
import sys
from unittest.mock import MagicMock

from dictate import daemon as D

# Replace hardware components with MagicMocks
D.Transcriber = lambda *a, **kw: MagicMock(device="cpu", compute_type="int8", last_error=None)
D.Recorder = lambda *a, **kw: MagicMock(start=lambda: None,
                                        stop=lambda: __import__("numpy").zeros(0))
# Keep HotkeyListener but skip pynput:
original = D.HotkeyListener


class FakeHL:
    def __init__(self, binding, mode, on_start, on_stop):
        self._state = MagicMock(recording=False)
        self.on_start, self.on_stop = on_start, on_stop
    def start(self): pass
    def stop(self): pass
    def external_toggle(self):
        self._state.recording = not self._state.recording
        (self.on_stop if not self._state.recording else self.on_start)()


D.HotkeyListener = FakeHL

sys.exit(D.main())
