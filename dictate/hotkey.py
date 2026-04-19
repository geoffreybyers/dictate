"""Hotkey binding parser + mode state machine. pynput wiring lives in Task 13."""
from __future__ import annotations

import enum
from typing import Callable


_MODIFIERS = {"ctrl", "shift", "alt", "super", "cmd", "meta"}


class Mode(enum.Enum):
    HOLD = "hold"
    TOGGLE = "toggle"


def parse_binding(binding: str) -> frozenset[str]:
    """Parse 'ctrl+shift+d' into a normalized keyset. Bare space requires modifier."""
    parts = [p.strip().lower() for p in binding.split("+") if p.strip()]
    if not parts:
        raise ValueError(f"empty hotkey binding: {binding!r}")
    keys = frozenset(parts)
    non_mod = keys - _MODIFIERS
    if "space" in non_mod and not (keys & _MODIFIERS):
        raise ValueError("hotkey 'space' requires a modifier (e.g. ctrl+space)")
    return keys


class HotkeyState:
    """State machine for recording sessions. Callbacks fire from arbitrary threads."""

    def __init__(
        self,
        mode: Mode,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
    ):
        self.mode = mode
        self._on_start = on_start
        self._on_stop = on_stop
        self._recording = False

    @property
    def recording(self) -> bool:
        return self._recording

    def on_combo_press(self) -> None:
        if self.mode is Mode.HOLD:
            if not self._recording:
                self._start()
        else:  # TOGGLE
            if self._recording:
                self._stop()
            else:
                self._start()

    def on_combo_release(self) -> None:
        if self.mode is Mode.HOLD and self._recording:
            self._stop()
        # TOGGLE: ignore releases

    def external_toggle(self) -> None:
        """SIGUSR1 entry point. Flips state regardless of mode."""
        if self._recording:
            self._stop()
        else:
            self._start()

    def _start(self) -> None:
        self._recording = True
        self._on_start()

    def _stop(self) -> None:
        self._recording = False
        self._on_stop()
