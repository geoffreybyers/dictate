import os
import signal
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from private_dictate.cli import main

_posix_only = pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX-only signals (SIGUSR1)"
)


def test_no_args_runs_daemon():
    with patch("private_dictate.cli.Daemon") as D:
        D.return_value.run.return_value = 0
        rc = main([])
        assert rc == 0
        D.return_value.run.assert_called_once()


def test_version(capsys):
    rc = main(["--version"])
    captured = capsys.readouterr()
    from private_dictate import __version__
    assert __version__ in captured.out
    assert rc == 0


@_posix_only
def test_toggle_sends_sigusr1(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    pid_dir = tmp_path / "private-dictate"
    pid_dir.mkdir()
    pid_file = pid_dir / "private-dictate.pid"
    pid_file.write_text(f"{os.getpid()}\n{int(0)}\n")
    with patch("private_dictate.cli.os.kill") as k:
        rc = main(["toggle"])
        # _read_pid() calls os.kill(pid, 0) for liveness; _signal_daemon() then
        # sends SIGUSR1. Mock sees both calls — check the last one was the signal.
        k.assert_called_with(os.getpid(), signal.SIGUSR1)
        assert rc == 0


@_posix_only
def test_toggle_no_daemon_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    rc = main(["toggle"])
    captured = capsys.readouterr()
    assert rc != 0
    assert "no" in captured.err.lower() and "daemon" in captured.err.lower()


def test_tui_no_daemon_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    rc = main(["tui"])
    captured = capsys.readouterr()
    assert rc != 0
    assert "no" in captured.err.lower() and "daemon" in captured.err.lower()
