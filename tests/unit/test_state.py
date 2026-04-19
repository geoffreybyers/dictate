import json
import os
from pathlib import Path

import pytest
from dictate.state import StateWriter, StatusSnapshot, HistoryEntry


def test_write_pid_then_clear(tmp_path: Path):
    sw = StateWriter(cache_dir=tmp_path, data_dir=tmp_path)
    sw.write_pid()
    assert (tmp_path / "dictate.pid").exists()
    body = (tmp_path / "dictate.pid").read_text().splitlines()
    assert int(body[0]) == os.getpid()
    sw.clear_pid()
    assert not (tmp_path / "dictate.pid").exists()


def test_write_status_atomic(tmp_path: Path):
    sw = StateWriter(cache_dir=tmp_path, data_dir=tmp_path)
    snap = StatusSnapshot(state="idle", recording=False, queue_depth=0,
                          last_error=None, pid=os.getpid(), uptime_s=12)
    sw.write_status(snap)
    path = tmp_path / "status.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["state"] == "idle"
    assert data["pid"] == os.getpid()
    # no temp leftovers
    assert not any(p.name.endswith(".tmp") for p in tmp_path.iterdir())


def test_history_append_jsonl(tmp_path: Path):
    sw = StateWriter(cache_dir=tmp_path, data_dir=tmp_path)
    sw.append_history(HistoryEntry(ts="2026-04-18T15:20:00Z", text="hello",
                                   duration_ms=1200, language="en", confidence=0.9))
    sw.append_history(HistoryEntry(ts="2026-04-18T15:21:00Z", text="world",
                                   duration_ms=800, language="en", confidence=0.8))
    lines = (tmp_path / "history.jsonl").read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["text"] == "hello"
    assert json.loads(lines[1])["text"] == "world"


def test_history_rotation_at_limit(tmp_path: Path):
    sw = StateWriter(cache_dir=tmp_path, data_dir=tmp_path, history_limit=3)
    for i in range(5):
        sw.append_history(HistoryEntry(ts=f"t{i}", text=f"entry-{i}",
                                       duration_ms=100, language="en", confidence=1.0))
    lines = (tmp_path / "history.jsonl").read_text().splitlines()
    assert len(lines) == 3
    # oldest two dropped, keeping entries 2, 3, 4
    texts = [json.loads(l)["text"] for l in lines]
    assert texts == ["entry-2", "entry-3", "entry-4"]
