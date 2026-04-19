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


# --- pynput wiring -----------------------------------------------------------

try:
    from pynput import keyboard  # type: ignore
except Exception:  # pragma: no cover — env without display
    keyboard = None


_KEY_ALIASES = {
    "ctrl_l": "ctrl", "ctrl_r": "ctrl",
    "shift_l": "shift", "shift_r": "shift",
    "alt_l": "alt", "alt_r": "alt", "alt_gr": "alt",
    "cmd_l": "cmd", "cmd_r": "cmd", "cmd": "cmd",
}


def _key_name(key) -> str | None:
    """Normalize a pynput key/keycode to the names used in parse_binding."""
    # KeyCode (printable)
    char = getattr(key, "char", None)
    if char:
        return char.lower()
    name = getattr(key, "name", None)
    if not name:
        return None
    return _KEY_ALIASES.get(name.lower(), name.lower())


class HotkeyListener:
    """Listens for the configured combo using pynput; drives HotkeyState."""

    def __init__(self, binding: str, mode: Mode,
                 on_start, on_stop):
        self._target = parse_binding(binding)
        self._state = HotkeyState(mode, on_start=on_start, on_stop=on_stop)
        self._pressed: set[str] = set()
        self._combo_active = False
        self._listener = None

    def start(self) -> None:
        if keyboard is None:
            raise RuntimeError("pynput.keyboard unavailable")
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    def external_toggle(self) -> None:
        self._state.external_toggle()

    def _on_press(self, key):
        name = _key_name(key)
        if name is None:
            return
        self._pressed.add(name)
        if not self._combo_active and self._target.issubset(self._pressed):
            self._combo_active = True
            self._state.on_combo_press()

    def _on_release(self, key):
        name = _key_name(key)
        if name is None:
            return
        self._pressed.discard(name)
        if self._combo_active and not self._target.issubset(self._pressed):
            self._combo_active = False
            self._state.on_combo_release()
