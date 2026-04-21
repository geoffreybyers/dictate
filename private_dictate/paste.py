"""Auto-paste: pynput on X11/mac/Win, ydotool shell-out on Wayland."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import Protocol

from private_dictate.errors import PasteUnavailableError

log = logging.getLogger(__name__)


class Backend(Protocol):
    def paste(self, shortcut: str) -> None: ...


class PynputBackend:
    """X11 / macOS / Windows. Uses pynput.keyboard."""

    def __init__(self, keyboard=None):
        if keyboard is None:
            from pynput.keyboard import Controller  # lazy import
            keyboard = Controller()
        self._kb = keyboard
        # Defer pynput.keyboard.Key import for testability
        from pynput.keyboard import Key
        self._Key = Key

    def paste(self, shortcut: str) -> None:
        keys = _parse_shortcut(shortcut, self._Key)
        try:
            for k in keys:
                self._kb.press(k)
            for k in reversed(keys):
                self._kb.release(k)
        except Exception as e:
            raise PasteUnavailableError(f"pynput paste failed: {e}") from e


class WaylandYdotoolBackend:
    """Wayland fallback — shells out to ydotool."""

    def paste(self, shortcut: str) -> None:
        # ydotool key syntax: "ctrl+v"
        try:
            r = subprocess.run(["ydotool", "key", shortcut],
                               capture_output=True, timeout=2)
        except FileNotFoundError as e:
            raise PasteUnavailableError("ydotool not installed") from e
        except subprocess.TimeoutExpired as e:
            raise PasteUnavailableError("ydotool timed out") from e
        if r.returncode != 0:
            raise PasteUnavailableError(
                f"ydotool failed: rc={r.returncode} stderr={r.stderr!r}"
            )


def _parse_shortcut(shortcut: str, Key):
    """'ctrl+v' → [Key.ctrl, 'v']. Modifier order preserved."""
    mod_map = {"ctrl": Key.ctrl, "shift": Key.shift, "alt": Key.alt,
               "super": Key.cmd, "cmd": Key.cmd, "meta": Key.cmd}
    out = []
    for part in shortcut.lower().split("+"):
        part = part.strip()
        out.append(mod_map.get(part, part))
    return out


def select_backend(session: str | None = None, platform: str | None = None) -> Backend:
    session = session or os.environ.get("XDG_SESSION_TYPE", "")
    platform = platform or sys.platform
    if platform == "linux" and session == "wayland":
        return WaylandYdotoolBackend()
    return PynputBackend()


def paste(shortcut: str) -> None:
    """Fire-and-forget simulated paste. Swallows PasteUnavailableError by logging."""
    try:
        select_backend().paste(shortcut)
    except PasteUnavailableError as e:
        log.warning("autopaste unavailable: %s — clipboard-only", e)
