"""PID file, status.json, history.jsonl — all writes are atomic."""
from __future__ import annotations

import json
import os
import time
from collections import deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class StatusSnapshot:
    state: str                          # "idle" | "recording" | "transcribing" | "downloading_model" | "error"
    recording: bool
    queue_depth: int
    last_error: Optional[str]
    pid: int
    uptime_s: int
    model_loaded: bool = False
    needs_restart: bool = False


@dataclass
class HistoryEntry:
    ts: str
    text: str
    duration_ms: int
    language: str
    confidence: float


class StateWriter:
    def __init__(self, cache_dir: Path, data_dir: Path, history_limit: int = 100):
        self.cache_dir = Path(cache_dir)
        self.data_dir = Path(data_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.history_limit = history_limit
        self._started_at = time.monotonic()

    @property
    def pid_path(self) -> Path:
        return self.cache_dir / "dictate.pid"

    @property
    def status_path(self) -> Path:
        return self.cache_dir / "status.json"

    @property
    def history_path(self) -> Path:
        return self.data_dir / "history.jsonl"

    def uptime_s(self) -> int:
        return int(time.monotonic() - self._started_at)

    def write_pid(self) -> None:
        body = f"{os.getpid()}\n{int(time.time())}\n"
        _atomic_write_text(self.pid_path, body)

    def clear_pid(self) -> None:
        try:
            self.pid_path.unlink()
        except FileNotFoundError:
            pass

    def write_status(self, snap: StatusSnapshot) -> None:
        _atomic_write_text(self.status_path, json.dumps(asdict(snap)) + "\n")

    def append_history(self, entry: HistoryEntry) -> None:
        line = json.dumps(asdict(entry)) + "\n"
        with open(self.history_path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        self._rotate_history_if_needed()

    def _rotate_history_if_needed(self) -> None:
        if not self.history_path.exists():
            return
        with open(self.history_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) <= self.history_limit:
            return
        kept = lines[-self.history_limit:]
        _atomic_write_text(self.history_path, "".join(kept))


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
