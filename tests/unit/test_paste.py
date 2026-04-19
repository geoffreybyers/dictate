from unittest.mock import patch, MagicMock
import pytest
from dictate.paste import paste, select_backend, WaylandYdotoolBackend, PynputBackend
from dictate.errors import PasteUnavailableError


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
    with patch("dictate.paste.subprocess.run") as run:
        run.return_value.returncode = 0
        be = WaylandYdotoolBackend()
        be.paste("ctrl+v")
        args, _ = run.call_args
        assert args[0][0] == "ydotool"


def test_paste_wayland_missing_ydotool_raises_unavailable():
    with patch("dictate.paste.subprocess.run", side_effect=FileNotFoundError):
        be = WaylandYdotoolBackend()
        with pytest.raises(PasteUnavailableError):
            be.paste("ctrl+v")
