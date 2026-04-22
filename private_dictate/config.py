"""Config schema, defaults, TOML load/save. Atomic writes; bad fields fall back with logs."""
from __future__ import annotations

import logging
import os
import tomllib
from dataclasses import dataclass, field, asdict
from pathlib import Path

log = logging.getLogger(__name__)


DEFAULT_CONFIG_TOML = """\
# private-dictate config — see `private-dictate tui` for an interactive editor.
# Daemon reloads this file on SIGHUP. Fields marked [restart] require
# `private-dictate` to be restarted.

[hotkey]
binding = "ctrl+shift+d"
mode = "hold"                # "hold" | "toggle"

[model]
size          = "small"      # "small" | "medium"             [restart]
device        = "auto"       # "auto" | "cpu" | "cuda"        [restart]
compute_type  = "auto"       # "auto" | "int8" | "int8_float32" | "float32" | "float16" | "int8_float16"
                             # float16/int8_float16 need CUDA + cuDNN; int8/int8_float32/float32 work on CPU too.
cache_dir     = ""

[transcription]
language         = "auto"
max_seconds      = 180
autopaste        = true
paste_shortcut   = "ctrl+v"
verbose_metadata = false

[audio]
microphone = ""

[history]
save  = true
limit = 100

[logs]
level       = "info"
max_size_mb = 10

[tui]
theme = "auto"
"""


@dataclass
class HotkeyCfg:
    binding: str = "ctrl+shift+d"
    mode: str = "hold"  # "hold" | "toggle"


@dataclass
class ModelCfg:
    size: str = "small"
    device: str = "auto"
    compute_type: str = "auto"
    cache_dir: str = ""


@dataclass
class TranscriptionCfg:
    language: str = "auto"
    max_seconds: int = 180
    autopaste: bool = True
    paste_shortcut: str = "ctrl+v"
    verbose_metadata: bool = False


@dataclass
class AudioCfg:
    microphone: str = ""


@dataclass
class HistoryCfg:
    save: bool = True
    limit: int = 100


@dataclass
class LogsCfg:
    level: str = "info"
    max_size_mb: int = 10


@dataclass
class TuiCfg:
    theme: str = "auto"


@dataclass
class Config:
    hotkey: HotkeyCfg = field(default_factory=HotkeyCfg)
    model: ModelCfg = field(default_factory=ModelCfg)
    transcription: TranscriptionCfg = field(default_factory=TranscriptionCfg)
    audio: AudioCfg = field(default_factory=AudioCfg)
    history: HistoryCfg = field(default_factory=HistoryCfg)
    logs: LogsCfg = field(default_factory=LogsCfg)
    tui: TuiCfg = field(default_factory=TuiCfg)


_HOTKEY_MODES = {"hold", "toggle"}
_MODEL_SIZES = {"small", "medium"}
_DEVICES = {"auto", "cpu", "cuda"}
_COMPUTE_TYPES = {"auto", "int8", "int8_float32", "float32", "float16", "int8_float16"}
_PASTE_SHORTCUTS = {"ctrl+v", "ctrl+shift+v"}
_LOG_LEVELS = {"debug", "info", "warn", "error"}
_THEMES = {"auto", "dark", "light"}


def _apply_table(target: object, table: dict, allowed: dict[str, set[str] | None]) -> None:
    """Copy valid fields from a parsed TOML table onto a dataclass instance."""
    for key, allowed_values in allowed.items():
        if key not in table:
            continue
        val = table[key]
        if allowed_values is not None and val not in allowed_values:
            log.warning("config: invalid %s=%r; falling back to default %r",
                        f"{type(target).__name__}.{key}", val, getattr(target, key))
            continue
        setattr(target, key, val)


def load(path: Path) -> Config:
    """Load config from TOML. Creates default file if missing. Bad fields fall back."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(DEFAULT_CONFIG_TOML)
        log.info("first-run config created at %s", path)

    cfg = Config()
    try:
        data = tomllib.loads(path.read_text())
    except (tomllib.TOMLDecodeError, OSError) as e:
        log.warning("config: failed to parse %s: %s — using defaults", path, e)
        return cfg

    _apply_table(cfg.hotkey, data.get("hotkey", {}),
                 {"binding": None, "mode": _HOTKEY_MODES})
    _apply_table(cfg.model, data.get("model", {}),
                 {"size": _MODEL_SIZES, "device": _DEVICES,
                  "compute_type": _COMPUTE_TYPES, "cache_dir": None})
    _apply_table(cfg.transcription, data.get("transcription", {}),
                 {"language": None, "max_seconds": None, "autopaste": None,
                  "paste_shortcut": _PASTE_SHORTCUTS, "verbose_metadata": None})
    _apply_table(cfg.audio, data.get("audio", {}), {"microphone": None})
    _apply_table(cfg.history, data.get("history", {}),
                 {"save": None, "limit": None})
    _apply_table(cfg.logs, data.get("logs", {}),
                 {"level": _LOG_LEVELS, "max_size_mb": None})
    _apply_table(cfg.tui, data.get("tui", {}), {"theme": _THEMES})

    return cfg


def save(cfg: Config, path: Path) -> None:
    """Atomic write: serialize, write temp, fsync, rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = _serialize(cfg)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(body)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _serialize(cfg: Config) -> str:
    """Minimal TOML serializer — avoids a tomli-w dependency."""
    def render(header: str, obj) -> str:
        lines = [f"[{header}]"]
        for k, v in asdict(obj).items():
            lines.append(f"{k} = {_fmt(v)}")
        return "\n".join(lines)

    parts = [
        render("hotkey", cfg.hotkey),
        render("model", cfg.model),
        render("transcription", cfg.transcription),
        render("audio", cfg.audio),
        render("history", cfg.history),
        render("logs", cfg.logs),
        render("tui", cfg.tui),
    ]
    return "\n\n".join(parts) + "\n"


def _fmt(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'
    raise TypeError(f"unsupported TOML value type: {type(v).__name__}")
