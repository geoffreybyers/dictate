"""Status screen — big state indicator, hotkey, model, uptime."""
from __future__ import annotations

import json
from pathlib import Path

from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Static

from private_dictate import paths


class StatusScreen(Widget):
    DEFAULT_CSS = """
    StatusScreen { padding: 1 2; }
    #status-state { text-style: bold; content-align: center middle; height: 5; }
    #status-info { margin-top: 1; }
    #status-model { margin-top: 1; }
    #status-notice { margin-top: 1; color: $warning; }
    #status-restart { margin-top: 1; color: $warning; text-style: bold; }
    #status-error { margin-top: 1; color: $error; }
    """

    def compose(self):
        yield Vertical(
            Static("", id="status-state"),
            Static("", id="status-info"),
            Static("", id="status-model"),
            Static("", id="status-restart"),
            Static("", id="status-notice"),
            Static("", id="status-error"),
        )

    def on_mount(self) -> None:
        self.set_interval(0.2, self._refresh)
        self._refresh()

    def _refresh(self) -> None:
        path = paths.cache_dir() / "status.json"
        if not path.exists():
            self.query_one("#status-state", Static).update("(no daemon running)")
            for wid in ("#status-info", "#status-model", "#status-restart",
                        "#status-notice", "#status-error"):
                self.query_one(wid, Static).update("")
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
        device = data.get("device") or "?"
        compute = data.get("compute_type") or "?"
        self.query_one("#status-model", Static).update(f"model: {device} / {compute}")
        needs_restart = bool(data.get("needs_restart"))
        self.query_one("#status-restart", Static).update(
            "⟳ config changed — restart daemon to apply" if needs_restart else ""
        )
        notice = data.get("model_notice") or ""
        self.query_one("#status-notice", Static).update(f"⚠ {notice}" if notice else "")
        err = data.get("last_error") or ""
        self.query_one("#status-error", Static).update(f"error: {err}" if err else "")
