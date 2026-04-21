import json
from pathlib import Path

import pytest

from private_dictate.tui.app import PrivateDictateTUI


@pytest.mark.asyncio
async def test_footer_renders_status(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    status_dir = tmp_path / "private-dictate"
    status_dir.mkdir()
    (status_dir / "status.json").write_text(json.dumps({
        "state": "idle", "recording": False, "queue_depth": 0,
        "last_error": None, "pid": 1234, "uptime_s": 5,
        "model_loaded": True, "needs_restart": False,
    }))
    app = PrivateDictateTUI()
    async with app.run_test() as pilot:
        await pilot.pause()
        rendered = app.query_one("#status-footer").render().plain
        assert "idle" in rendered.lower()


@pytest.mark.asyncio
async def test_sidebar_navigation(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    app = PrivateDictateTUI()
    async with app.run_test() as pilot:
        await pilot.press("s")
        assert app.current_screen_name == "settings"
        await pilot.press("h")
        assert app.current_screen_name == "history"
