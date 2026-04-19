"""Status screen — big state indicator, hotkey, model, uptime."""
from __future__ import annotations

import json
from pathlib import Path

from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Static

from dictate import paths


class StatusScreen(Widget):
    DEFAULT_CSS = """
    StatusScreen { padding: 1 2; }
    #status-state { text-style: bold; content-align: center middle; height: 5; }
    #status-info { margin-top: 1; }
    """

    def compose(self):
        yield Vertical(
            Static("", id="status-state"),
            Static("", id="status-info"),
        )

    def on_mount(self) -> None:
        self.set_interval(0.2, self._refresh)
        self._refresh()

    def _refresh(self) -> None:
        path = paths.cache_dir() / "status.json"
        if not path.exists():
            self.query_one("#status-state", Static).update("(no daemon running)")
            self.query_one("#status-info", Static).update("")
            return
        try:
            data = json.loads(path.read_text())
        except Exception:
            return
        state = data.get("state", "unknown")
        self.query_one("#status-state", Static).update(state.upper())
        info = [
            f"pid: {data.get('pid')}",
            f"uptime: {data.get('uptime_s')}s",
            f"queue: {data.get('queue_depth')}",
        ]
        self.query_one("#status-info", Static).update(" · ".join(info))
