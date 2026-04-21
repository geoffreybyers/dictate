"""Live status footer — polls status.json at 10 Hz."""
from __future__ import annotations

import json
from pathlib import Path

from textual.widgets import Static

from private_dictate import paths


class StatusFooter(Static):
    def on_mount(self) -> None:
        self.set_interval(0.1, self._refresh)
        self._refresh()

    def _refresh(self) -> None:
        path = paths.cache_dir() / "status.json"
        if not path.exists():
            self.update("(no daemon)")
            return
        try:
            data = json.loads(path.read_text())
        except Exception:
            self.update("(status unreadable)")
            return
        state = data.get("state", "unknown")
        queue = data.get("queue_depth", 0)
        err = data.get("last_error")
        if err:
            self.update(f"⚠ error: {err}")
            return
        suffix = f" · queue: {queue}" if queue else ""
        self.update(f"{state}{suffix}")
