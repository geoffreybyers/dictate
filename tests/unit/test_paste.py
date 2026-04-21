import sys
import types
from unittest.mock import patch, MagicMock
import pytest
from private_dictate.paste import paste, select_backend, WaylandYdotoolBackend, PynputBackend
from private_dictate.errors import PasteUnavailableError


@pytest.fixture(autouse=True)
def _stub_pynput_keyboard(monkeypatch):
    # Real pynput eagerly loads a platform backend at import time (xorg on Linux),
    # which fails on headless CI. Stub the module so these tests exercise only
    # private_dictate.paste's logic.
    fake_keyboard = types.ModuleType("pynput.keyboard")
    fake_keyboard.Controller = MagicMock
    fake_keyboard.Key = types.SimpleNamespace(
        ctrl="ctrl", shift="shift", alt="alt", cmd="cmd"
    )
    fake_pynput = types.ModuleType("pynput")
    fake_pynput.keyboard = fake_keyboard
    monkeypatch.setitem(sys.modules, "pynput", fake_pynput)
    monkeypatch.setitem(sys.modules, "pynput.keyboard", fake_keyboard)


def test_select_backend_wayland_picks_ydotool():
    be = select_backend(session="wayland", platform="linux")
    assert isinstance(be, WaylandYdotoolBackend)


def test_select_backend_x11_picks_pynput():
    be = select_backend(session="x11", platform="linux")
    assert isinstance(be, PynputBackend)


def test_select_backend_macos_picks_pynput():
    be = select_backend(session="", platform="darwin")
    assert isinstance(be, PynputBackend)


def test_select_backend_windows_picks_pynput():
    be = select_backend(session="", platform="win32")
    assert isinstance(be, PynputBackend)


def test_paste_pynput_success_presses_ctrl_v():
    mock_kb = MagicMock()
    be = PynputBackend(keyboard=mock_kb)
    be.paste("ctrl+v")
    # press + release called for ctrl and v
    assert mock_kb.press.call_count == 2
    assert mock_kb.release.call_count == 2


def test_paste_wayland_shells_out_to_ydotool():
    with patch("private_dictate.paste.subprocess.run") as run:
        run.return_value.returncode = 0
        be = WaylandYdotoolBackend()
        be.paste("ctrl+v")
        args, _ = run.call_args
        assert args[0][0] == "ydotool"


def test_paste_wayland_missing_ydotool_raises_unavailable():
    with patch("private_dictate.paste.subprocess.run", side_effect=FileNotFoundError):
        be = WaylandYdotoolBackend()
        with pytest.raises(PasteUnavailableError):
            be.paste("ctrl+v")
