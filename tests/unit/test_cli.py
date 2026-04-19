import os
import signal
from pathlib import Path
from unittest.mock import patch
from dictate.cli import main


def test_dictate_no_args_runs_daemon():
    with patch("dictate.cli.Daemon") as D:
        D.return_value.run.return_value = 0
        rc = main([])
        assert rc == 0
        D.return_value.run.assert_called_once()


def test_dictate_version(capsys):
    rc = main(["--version"])
    captured = capsys.readouterr()
    from dictate import __version__
    assert __version__ in captured.out
    assert rc == 0


def test_dictate_toggle_sends_sigusr1(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    pid_dir = tmp_path / "dictate"
    pid_dir.mkdir()
    pid_file = pid_dir / "dictate.pid"
    pid_file.write_text(f"{os.getpid()}\n{int(0)}\n")
    with patch("dictate.cli.os.kill") as k:
        rc = main(["toggle"])
        # _read_pid() calls os.kill(pid, 0) for liveness; _signal_daemon() then
        # sends SIGUSR1. Mock sees both calls — check the last one was the signal.
        k.assert_called_with(os.getpid(), signal.SIGUSR1)
        assert rc == 0


def test_dictate_toggle_no_daemon_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    rc = main(["toggle"])
    captured = capsys.readouterr()
    assert rc != 0
    assert "no" in captured.err.lower() and "daemon" in captured.err.lower()


def test_dictate_tui_no_daemon_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    rc = main(["tui"])
    captured = capsys.readouterr()
    assert rc != 0
    assert "no" in captured.err.lower() and "daemon" in captured.err.lower()
