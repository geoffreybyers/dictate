from unittest.mock import MagicMock, patch
from private_dictate.hotkey import HotkeyListener, Mode


def test_listener_starts_and_stops():
    with patch("private_dictate.hotkey.keyboard") as kb:
        listener_instance = MagicMock()
        kb.Listener.return_value = listener_instance
        hl = HotkeyListener("ctrl+shift+d", Mode.HOLD,
                            on_start=lambda: None, on_stop=lambda: None)
        hl.start()
        listener_instance.start.assert_called_once()
        hl.stop()
        listener_instance.stop.assert_called_once()


def test_listener_press_release_drives_state_machine():
    with patch("private_dictate.hotkey.keyboard") as kb:
        events = []
        kb.Listener.return_value = MagicMock()
        hl = HotkeyListener("ctrl+shift+d", Mode.HOLD,
                            on_start=lambda: events.append("start"),
                            on_stop=lambda: events.append("stop"))
        # Simulate the full combo being held
        hl._on_press(_make_key(kb, "ctrl"))
        hl._on_press(_make_key(kb, "shift"))
        hl._on_press(_make_key(kb, "d"))
        assert events == ["start"]
        hl._on_release(_make_key(kb, "d"))
        assert events == ["start", "stop"]


def _make_key(kb_mock, name):
    """Fake a pynput.keyboard.KeyCode or Key with our naming."""
    k = MagicMock()
    k.char = None
    # Exploit the name resolution in _key_name
    if name in {"ctrl", "shift", "alt", "super", "cmd", "meta"}:
        k.name = name
    else:
        k.char = name
    return k
