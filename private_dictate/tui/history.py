"""History screen — scrollable list of transcriptions."""
from __future__ import annotations

import datetime as dt
import json

from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Static

from dictate import paths


class HistoryScreen(Widget):
    DEFAULT_CSS = """
    HistoryScreen { padding: 1 2; }
    #history-list { height: 1fr; overflow-y: auto; }
    .hist-entry { padding: 0 0 1 0; }
    .hist-ts { color: $text-muted; }
    """

    def compose(self):
        yield Vertical(Static("", id="history-list"))

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        path = paths.data_dir() / "history.jsonl"
        if not path.exists():
            self.query_one("#history-list", Static).update(
                "No transcriptions yet.")
            return
        lines = path.read_text().splitlines()
        entries = []
        for line in lines[-100:]:
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
        # group by local date
        buckets: dict[str, list[dict]] = {}
        for e in entries:
            day = _date_label(e.get("ts", ""))
            buckets.setdefault(day, []).append(e)
        out = []
        for day, items in buckets.items():
            out.append(f"[b]{day}[/]")
            for e in items:
                out.append(f"  [dim]{_short_ts(e.get('ts',''))}[/] {e.get('text','')}")
        self.query_one("#history-list", Static).update("\n".join(out))


def _date_label(iso_ts: str) -> str:
    try:
        d = dt.datetime.fromisoformat(iso_ts).astimezone()
        today = dt.datetime.now().astimezone().date()
        delta = (today - d.date()).days
        if delta == 0:
            return "Today"
        if delta == 1:
            return "Yesterday"
        return d.date().isoformat()
    except Exception:
        return iso_ts or "(unknown)"


def _short_ts(iso_ts: str) -> str:
    try:
        d = dt.datetime.fromisoformat(iso_ts).astimezone()
        return d.strftime("%H:%M:%S")
    except Exception:
        return iso_ts[:19]
