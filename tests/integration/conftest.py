import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest


@pytest.fixture
def dictate_env(tmp_path: Path):
    """Isolate XDG dirs so the test daemon doesn't touch user state."""
    env = os.environ.copy()
    env["XDG_CONFIG_HOME"] = str(tmp_path / "config")
    env["XDG_CACHE_HOME"] = str(tmp_path / "cache")
    env["XDG_DATA_HOME"] = str(tmp_path / "data")
    yield env


@pytest.fixture
def spawn_daemon(dictate_env, monkeypatch):
    """Launch the daemon as a subprocess with heavy components stubbed out.

    The subprocess loads a small monkey-patch module first that replaces
    Transcriber / Recorder / HotkeyListener with fakes.
    """
    stub_path = Path(__file__).parent / "_stub_daemon.py"
    proc = subprocess.Popen(
        [sys.executable, str(stub_path)],
        env=dictate_env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    # wait for PID file to appear (up to 5s)
    pid_file = Path(dictate_env["XDG_CACHE_HOME"]) / "dictate" / "dictate.pid"
    for _ in range(50):
        if pid_file.exists():
            break
        time.sleep(0.1)
    else:
        proc.kill()
        out, err = proc.communicate(timeout=2)
        raise RuntimeError(f"daemon did not start: stdout={out!r} stderr={err!r}")
    yield proc, pid_file
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    # Drain and close pipes to avoid ResourceWarning (filterwarnings=error)
    try:
        proc.communicate(timeout=2)
    except (subprocess.TimeoutExpired, ValueError):
        pass
    if proc.stdout:
        proc.stdout.close()
    if proc.stderr:
        proc.stderr.close()
