"""pynput push-to-talk listener with debounce."""

import threading

from pynput import keyboard


def _parse_hotkey(hotkey_str: str) -> keyboard.Key | keyboard.KeyCode:
    """Map config hotkey string to pynput Key or KeyCode."""
    normalized = hotkey_str.lower().replace("-", "_")
    try:
        key_attr = getattr(keyboard.Key, normalized)
        return key_attr
    except AttributeError:
        pass
    if len(hotkey_str) == 1:
        return keyboard.KeyCode.from_char(hotkey_str)
    # Multi-char (e.g. "f9" as string) — try Key again with exact name
    try:
        return getattr(keyboard.Key, hotkey_str.replace("-", "_"))
    except AttributeError:
        return keyboard.KeyCode.from_char(hotkey_str)


def _keys_match(key: keyboard.Key | keyboard.KeyCode, target: keyboard.Key | keyboard.KeyCode) -> bool:
    """Return True if the event key matches the configured hotkey."""
    if type(key) != type(target):
        return False
    if isinstance(target, keyboard.Key):
        return key == target
    # KeyCode: compare char if both have it, else vk
    kc_key = key
    kc_target = target
    if getattr(kc_key, "char", None) is not None and getattr(kc_target, "char", None) is not None:
        return kc_key.char == kc_target.char
    return getattr(kc_key, "vk", None) == getattr(kc_target, "vk", None)


class HotkeyListener:
    """Listens globally for hotkey; calls on_press once per key-down, on_release once per key-up."""

    def __init__(
        self,
        hotkey: str,
        on_press: callable,
        on_release: callable,
    ) -> None:
        self._hotkey_key = _parse_hotkey(hotkey)
        self._on_press = on_press
        self._on_release = on_release
        self._key_pressed = False
        self._listener: keyboard.Listener | None = None
        self._daemon_thread: threading.Thread | None = None

    def _on_press_inner(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if _keys_match(key, self._hotkey_key) and not self._key_pressed:
            self._key_pressed = True
            self._on_press()

    def _on_release_inner(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if _keys_match(key, self._hotkey_key):
            self._key_pressed = False
            self._on_release()

    def start(self) -> None:
        self._listener = keyboard.Listener(
            on_press=self._on_press_inner,
            on_release=self._on_release_inner,
        )
        self._listener.start()
        self._daemon_thread = threading.Thread(target=self._listener.join, daemon=True)
        self._daemon_thread.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._daemon_thread = None
