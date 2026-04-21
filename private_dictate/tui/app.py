"""Textual app root. Three screens: Status, Settings, History."""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Static, ListView, ListItem, Label

from dictate.tui.footer import StatusFooter
from dictate.tui.status import StatusScreen


class Sidebar(ListView):
    DEFAULT_CSS = "Sidebar { width: 20; border-right: solid $accent; }"


class DictateTUI(App):
    CSS = """
    Screen { layout: vertical; }
    #body { height: 1fr; }
    #content { padding: 1 2; }
    #status-footer { dock: bottom; height: 1; background: $boost; padding: 0 1; }
    """
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "jump('settings')", "Settings"),
        ("h", "jump('history')", "History"),
        ("t", "jump('status')", "Status"),
    ]

    def __init__(self):
        super().__init__()
        self.current_screen_name = "status"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="body"):
            yield Sidebar(
                ListItem(Label("Status"), id="nav-status"),
                ListItem(Label("Settings"), id="nav-settings"),
                ListItem(Label("History"), id="nav-history"),
            )
            yield Vertical(StatusScreen(id="screen-body"), id="content")
        yield StatusFooter(id="status-footer")

    async def action_jump(self, name: str) -> None:
        self.current_screen_name = name
        content = self.query_one("#content")
        # Remove all existing children
        for child in list(content.children):
            await child.remove()
        if name == "status":
            content.mount(StatusScreen(id="screen-body"))
        elif name == "settings":
            from dictate.tui.settings import SettingsScreen
            content.mount(SettingsScreen(id="screen-body"))
        elif name == "history":
            from dictate.tui.history import HistoryScreen
            content.mount(HistoryScreen(id="screen-body"))


def run_tui() -> int:
    DictateTUI().run()
    return 0
