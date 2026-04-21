"""Settings screen — flat form, explicit Save (Ctrl+S)."""
from __future__ import annotations

import os
import signal
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widget import Widget
from textual.widgets import Static, Input, Switch, Select, Button, Label

from dictate import paths
from dictate.config import (
    Config, load as load_cfg, save as save_cfg,
    _HOTKEY_MODES, _MODEL_SIZES, _DEVICES, _COMPUTE_TYPES,
    _PASTE_SHORTCUTS, _LOG_LEVELS, _THEMES,
)


_STRUCTURAL_FIELDS = {
    ("model", "size"), ("model", "device"), ("model", "compute_type"),
    ("model", "cache_dir"), ("audio", "microphone"),
}


class SettingsScreen(Widget):
    DEFAULT_CSS = """
    SettingsScreen { padding: 1 2; }
    .field-row { height: 3; align: left middle; }
    .field-label { width: 24; content-align: right middle; padding-right: 2; }
    .dirty-label { color: $warning; margin-left: 2; }
    #save-bar { dock: bottom; height: 3; border-top: solid $accent; padding: 0 2;
                align: right middle; display: none; }
    #save-bar.dirty { display: block; }
    """

    def __init__(self, **kw):
        super().__init__(**kw)
        self._cfg = load_cfg(paths.config_path())
        self._dirty: set[tuple[str, str]] = set()
        self._initial = _snapshot(self._cfg)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("[b]Hotkey[/]")
            yield from self._row("hotkey", "binding", "Binding",
                                 Input(value=self._cfg.hotkey.binding, id="field-hotkey-binding"))
            yield from self._row("hotkey", "mode", "Mode",
                                 Select(options=[(m, m) for m in sorted(_HOTKEY_MODES)],
                                        value=self._cfg.hotkey.mode,
                                        id="field-hotkey-mode"))

            yield Static("[b]Model[/]")
            yield from self._row("model", "size", "Size",
                                 Select(options=[(s, s) for s in sorted(_MODEL_SIZES)],
                                        value=self._cfg.model.size, id="field-model-size"))
            yield from self._row("model", "device", "Device",
                                 Select(options=[(d, d) for d in sorted(_DEVICES)],
                                        value=self._cfg.model.device, id="field-model-device"))
            yield from self._row("model", "compute_type", "Compute",
                                 Select(options=[(c, c) for c in sorted(_COMPUTE_TYPES)],
                                        value=self._cfg.model.compute_type,
                                        id="field-model-compute_type"))

            yield Static("[b]Transcription[/]")
            yield from self._row("transcription", "language", "Language",
                                 Input(value=self._cfg.transcription.language,
                                       id="field-transcription-language"))
            yield from self._row("transcription", "max_seconds", "Max seconds",
                                 Input(value=str(self._cfg.transcription.max_seconds),
                                       id="field-transcription-max_seconds"))
            yield from self._row("transcription", "autopaste", "Autopaste",
                                 Switch(value=self._cfg.transcription.autopaste,
                                        id="field-transcription-autopaste"))
            yield from self._row("transcription", "paste_shortcut", "Paste shortcut",
                                 Select(options=[(s, s) for s in sorted(_PASTE_SHORTCUTS)],
                                        value=self._cfg.transcription.paste_shortcut,
                                        id="field-transcription-paste_shortcut"))
            yield from self._row("transcription", "verbose_metadata", "Verbose metadata",
                                 Switch(value=self._cfg.transcription.verbose_metadata,
                                        id="field-transcription-verbose_metadata"))

            yield Static("[b]History[/]")
            yield from self._row("history", "save", "Save history",
                                 Switch(value=self._cfg.history.save, id="field-history-save"))
            yield from self._row("history", "limit", "Limit",
                                 Input(value=str(self._cfg.history.limit),
                                       id="field-history-limit"))

            yield Static("[b]TUI[/]")
            yield from self._row("tui", "theme", "Theme",
                                 Select(options=[(t, t) for t in sorted(_THEMES)],
                                        value=self._cfg.tui.theme, id="field-tui-theme"))

        with Horizontal(id="save-bar"):
            yield Button("Discard", id="discard-btn")
            yield Button("Save (Ctrl+S)", id="save-btn", variant="primary")

    def _row(self, section, field, label, widget):
        yield Horizontal(Label(label, classes="field-label"), widget, classes="field-row")

    def on_input_changed(self, event):   self._mark_dirty(event.input.id)
    def on_select_changed(self, event):  self._mark_dirty(event.select.id)
    def on_switch_changed(self, event):  self._mark_dirty(event.switch.id)

    def _mark_dirty(self, widget_id: str | None) -> None:
        if not widget_id or not widget_id.startswith("field-"):
            return
        _, section, field = widget_id.split("-", 2)
        self._dirty.add((section, field))
        self.query_one("#save-bar").set_class(True, "dirty")

    def on_button_pressed(self, event):
        if event.button.id == "save-btn":
            self._save()
        elif event.button.id == "discard-btn":
            self._discard()

    def key_ctrl_s(self) -> None:
        self._save()

    def _save(self) -> None:
        # Read values back into self._cfg
        for (section, field) in list(self._dirty):
            widget_id = f"#field-{section}-{field}"
            widget = self.query_one(widget_id)
            raw = getattr(widget, "value", None)
            target = getattr(self._cfg, section)
            # Coerce numerics
            current = getattr(target, field)
            if isinstance(current, int) and not isinstance(current, bool):
                try:
                    raw = int(raw)
                except (TypeError, ValueError):
                    continue
            setattr(target, field, raw)
        save_cfg(self._cfg, paths.config_path())
        self._dirty.clear()
        self.query_one("#save-bar").set_class(False, "dirty")
        self._signal_daemon()

    def _discard(self) -> None:
        # Reload from disk and reset UI state
        self._cfg = load_cfg(paths.config_path())
        self._dirty.clear()
        self.query_one("#save-bar").set_class(False, "dirty")
        # Simple approach: tell the app to remount the screen
        self.app.action_jump("settings")

    def _signal_daemon(self) -> None:
        pid_path = paths.cache_dir() / "dictate.pid"
        if not pid_path.exists():
            return
        try:
            pid = int(pid_path.read_text().splitlines()[0])
            os.kill(pid, signal.SIGHUP)
        except (OSError, ValueError):
            pass


def _snapshot(cfg: Config) -> dict:
    return {name: getattr(cfg, name).__dict__.copy() for name in cfg.__dict__}
