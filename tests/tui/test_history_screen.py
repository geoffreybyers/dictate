import json
import os
from pathlib import Path

import pytest

from dictate.tui.app import DictateTUI


@pytest.mark.asyncio
async def test_history_screen_lists_entries(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    # daemon-alive faked
    pd = tmp_path / "cache" / "dictate"; pd.mkdir(parents=True)
    (pd / "dictate.pid").write_text(f"{os.getpid()}\n0\n")
    # history file
    dd = tmp_path / "data" / "dictate"; dd.mkdir(parents=True)
    h = dd / "history.jsonl"
    h.write_text(
        json.dumps({"ts": "2026-04-18T10:00:00+00:00", "text": "first",
                    "duration_ms": 100, "language": "en", "confidence": 0.9}) + "\n" +
        json.dumps({"ts": "2026-04-18T10:05:00+00:00", "text": "second",
                    "duration_ms": 200, "language": "en", "confidence": 0.8}) + "\n"
    )
    app = DictateTUI()
    async with app.run_test() as pilot:
        await pilot.press("h")
        await pilot.pause()
        body = app.query_one("#history-list").render().plain
        assert "first" in body
        assert "second" in body
