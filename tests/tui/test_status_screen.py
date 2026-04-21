import json
from pathlib import Path

import pytest

from private_dictate.tui.app import PrivateDictateTUI


@pytest.mark.asyncio
async def test_status_screen_renders_state_fields(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    sd = tmp_path / "private-dictate"
    sd.mkdir()
    (sd / "status.json").write_text(json.dumps({
        "state": "recording", "recording": True, "queue_depth": 1,
        "last_error": None, "pid": 7, "uptime_s": 100,
        "model_loaded": True, "needs_restart": False,
    }))
    app = PrivateDictateTUI()
    async with app.run_test() as pilot:
        await pilot.pause()
        # Default screen is status
        state_widget = app.query_one("#status-state")
        assert "recording" in state_widget.render().plain.lower()
