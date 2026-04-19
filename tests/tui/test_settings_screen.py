import os
import signal
from pathlib import Path
from unittest.mock import patch

import pytest

from dictate.tui.app import DictateTUI
from dictate.tui.settings import SettingsScreen


@pytest.mark.asyncio
async def test_settings_edit_and_save_sends_sighup(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    # pretend a daemon is running at our own pid so os.kill(pid, 0) passes
    pid_dir = tmp_path / "cache" / "dictate"
    pid_dir.mkdir(parents=True)
    (pid_dir / "dictate.pid").write_text(f"{os.getpid()}\n0\n")

    app = DictateTUI()
    async with app.run_test() as pilot:
        await pilot.press("s")  # switch to settings screen
        await pilot.pause()
        screen = app.query_one(SettingsScreen)
        # Simulate a user edit: directly update the Input value and mark dirty
        binding_input = app.query_one("#field-hotkey-binding")
        binding_input.value = "F9"
        screen._dirty.add(("hotkey", "binding"))
        with patch("dictate.tui.settings.os.kill") as kill:
            screen._save()
            assert kill.called
            assert kill.call_args[0][1] == signal.SIGHUP
        cfg_path = tmp_path / "config" / "dictate" / "config.toml"
        assert "F9" in cfg_path.read_text()
