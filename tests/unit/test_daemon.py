"""We test the daemon's orchestration in isolation by mocking its hardware-facing
components. Full integration tests live in tests/integration."""
from unittest.mock import MagicMock, patch
from pathlib import Path
from dictate.config import Config


def test_daemon_wires_components_and_writes_pid(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    with patch("dictate.daemon.Transcriber") as T, \
         patch("dictate.daemon.Recorder") as R, \
         patch("dictate.daemon.HotkeyListener") as HK:
        T.return_value = MagicMock(device="cpu", compute_type="int8", last_error=None)
        from dictate.daemon import Daemon
        d = Daemon(cfg=Config())
        d.setup()
        pid_file = tmp_path / "cache" / "dictate" / "dictate.pid"
        assert pid_file.exists()
        T.assert_called_once()
        R.assert_called_once()
        HK.assert_called_once()


def test_sigusr1_forwards_to_external_toggle(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    with patch("dictate.daemon.Transcriber") as T, \
         patch("dictate.daemon.Recorder"), \
         patch("dictate.daemon.HotkeyListener") as HK:
        T.return_value = MagicMock(device="cpu", compute_type="int8", last_error=None)
        hk_instance = MagicMock()
        HK.return_value = hk_instance
        from dictate.daemon import Daemon
        d = Daemon(cfg=Config())
        d.setup()
        d._handle_sigusr1(0, None)
        hk_instance.external_toggle.assert_called_once()
