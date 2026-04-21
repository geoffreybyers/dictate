import json
import os
import signal
import time
from pathlib import Path


def _wait_status(cache_home: Path, predicate, timeout=5.0):
    path = Path(cache_home) / "private-dictate" / "status.json"
    start = time.time()
    while time.time() - start < timeout:
        if path.exists():
            try:
                data = json.loads(path.read_text())
                if predicate(data):
                    return data
            except Exception:
                pass
        time.sleep(0.1)
    raise AssertionError(f"status predicate never matched; last: {path.read_text() if path.exists() else None}")


def test_daemon_writes_pid_and_status(spawn_daemon, dictate_env):
    proc, pid_file = spawn_daemon
    assert pid_file.exists()
    pid_txt = pid_file.read_text().strip()
    assert int(pid_txt.splitlines()[0]) == proc.pid
    data = _wait_status(dictate_env["XDG_CACHE_HOME"], lambda d: d["state"] == "idle")
    assert data["pid"] == proc.pid


def test_sighup_reloads_config(spawn_daemon, dictate_env):
    proc, _ = spawn_daemon
    cfg_path = Path(dictate_env["XDG_CONFIG_HOME"]) / "private-dictate" / "config.toml"
    body = cfg_path.read_text()
    cfg_path.write_text(body.replace('verbose_metadata = false', 'verbose_metadata = true'))
    os.kill(proc.pid, signal.SIGHUP)
    time.sleep(0.3)
    # Process should still be alive
    assert proc.poll() is None


def test_sigterm_clean_exit_removes_pid(spawn_daemon, dictate_env):
    proc, pid_file = spawn_daemon
    os.kill(proc.pid, signal.SIGTERM)
    proc.wait(timeout=5)
    assert proc.returncode == 0
    assert not pid_file.exists()


def test_sigusr1_flips_recording_state(spawn_daemon, dictate_env):
    proc, _ = spawn_daemon
    _wait_status(dictate_env["XDG_CACHE_HOME"], lambda d: d["state"] == "idle")
    os.kill(proc.pid, signal.SIGUSR1)
    _wait_status(dictate_env["XDG_CACHE_HOME"], lambda d: d["recording"] is True, timeout=2)
    os.kill(proc.pid, signal.SIGUSR1)
    _wait_status(dictate_env["XDG_CACHE_HOME"], lambda d: d["recording"] is False, timeout=2)
