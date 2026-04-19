# dictate v2: replace GUI with TUI + Python daemon — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Tauri/React GUI with a pure-Python daemon + Textual TUI that share state via files and POSIX signals.

**Architecture:** Two Python processes. `dictate` runs the daemon foreground (user manages lifecycle via shell / tmux / systemd / autostart). `dictate tui` launches a Textual TUI that reads/writes `config.toml`, polls `status.json` at 10 Hz, and sends `SIGHUP` on config save. No sockets, no RPC.

**Tech Stack:** Python 3.11+, faster-whisper, sounddevice/PortAudio, pynput, pyperclip, Textual, tomllib (stdlib), pytest + pytest-asyncio.

**Spec:** [`docs/superpowers/specs/2026-04-18-cli-replaces-gui-design.md`](../specs/2026-04-18-cli-replaces-gui-design.md)

**Deviations from spec:**
- `queue.py` → `jobs.py` to avoid shadowing stdlib `queue`.

**Before starting:** Create a feature branch. All work lives there until the final merge.

```bash
git checkout -b rebuild/python-tui
```

---

## Phase 0 — Bootstrap

### Task 1: Delete old scaffolding; create empty Python package

**Files:**
- Delete: `src/`, `src-tauri/`, `sidecar/`, `dist/`, `public/`, `node_modules/`, `index.html`, `package.json`, `package-lock.json`, `vite.config.ts`, `tsconfig.json`, `tsconfig.node.json`, `tailwind.config.js`, `postcss.config.js`, `scripts/build-sidecar.sh`, `UI_SPEC.md`, the existing `dictate/` contents
- Create: `dictate/__init__.py`, `dictate/tui/__init__.py`, `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`, `tests/tui/__init__.py`

- [x] **Step 1: Delete old scaffolding**

```bash
rm -rf src src-tauri sidecar dist public node_modules
rm -f index.html package.json package-lock.json vite.config.ts tsconfig.json tsconfig.node.json tailwind.config.js postcss.config.js UI_SPEC.md
rm -f scripts/build-sidecar.sh
rm -rf dictate
```

- [x] **Step 2: Create empty Python package structure**

```bash
mkdir -p dictate/tui tests/unit tests/integration tests/tui
touch dictate/__init__.py dictate/tui/__init__.py
touch tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py tests/tui/__init__.py
```

Put a package docstring in `dictate/__init__.py`:

```python
"""dictate — offline, privacy-first speech-to-text."""

__version__ = "2.0.0.dev0"
```

- [x] **Step 3: Update .gitignore for Python**

Replace the Node/Rust entries in `.gitignore` with Python entries:

```
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
*.egg-info/
dist/
build/
.pytest_cache/
.coverage
htmlcov/

# dictate runtime files (when running from repo)
/config.toml
/dictate.pid
/status.json
/history.jsonl
/dictate.log
```

Keep pre-existing entries that still apply (e.g., OS files, editor).

- [x] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: delete Tauri/React/sidecar scaffolding; seed Python package"
```

---

### Task 2: pyproject.toml + dev environment

**Files:**
- Create: `pyproject.toml`, `requirements-dev.txt`

- [x] **Step 1: Write pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "dictate"
version = "2.0.0.dev0"
description = "Offline, privacy-first speech-to-text with a terminal UI."
readme = "README.md"
license = { file = "LICENSE" }
authors = [{ name = "Geoffrey Byers" }]
requires-python = ">=3.11"
dependencies = [
    "faster-whisper>=1.0.0",
    "sounddevice>=0.4.6",
    "numpy>=1.24",
    "pynput>=1.7.6",
    "pyperclip>=1.8.2",
    "textual>=0.50",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-asyncio>=0.23",
    "pytest-timeout>=2.2",
]

[project.scripts]
dictate = "dictate.cli:main"

[tool.setuptools.packages.find]
include = ["dictate*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
timeout = 30
filterwarnings = ["error"]
```

- [x] **Step 2: Write requirements-dev.txt (for convenience)**

```
-e .[dev]
```

- [x] **Step 3: Create virtualenv and install**

```bash
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements-dev.txt
```

Expected: all dependencies install. If `faster-whisper` wheels fail on your platform, consult its README before proceeding.

- [x] **Step 4: Verify `pytest` runs (no tests yet, should exit 5 "no tests collected")**

```bash
.venv/bin/pytest -q
```

Expected: `no tests ran in X.XX s` (exit code 5). Not an error for our purposes.

- [x] **Step 5: Commit**

```bash
git add pyproject.toml requirements-dev.txt
git commit -m "chore: add pyproject.toml with runtime + dev deps"
```

---

## Phase 1 — Data foundation

### Task 3: errors.py — typed exceptions

**Files:**
- Create: `dictate/errors.py`
- Test: `tests/unit/test_errors.py`

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_errors.py
from dictate.errors import (
    DictateError,
    ConfigError,
    AudioError,
    TranscriptionError,
    QueueOverflowError,
    PasteUnavailableError,
)


def test_all_errors_inherit_from_base():
    for cls in (ConfigError, AudioError, TranscriptionError, QueueOverflowError, PasteUnavailableError):
        assert issubclass(cls, DictateError)


def test_errors_carry_messages():
    err = ConfigError("bad value for hotkey.binding")
    assert "bad value for hotkey.binding" in str(err)
```

- [x] **Step 2: Run the test (fails with ImportError)**

```bash
.venv/bin/pytest tests/unit/test_errors.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'dictate.errors'`.

- [x] **Step 3: Implement `dictate/errors.py`**

```python
"""Typed exceptions used across dictate."""


class DictateError(Exception):
    """Base class for all dictate errors."""


class ConfigError(DictateError):
    """Invalid or unparseable configuration."""


class AudioError(DictateError):
    """Microphone / recording failed."""


class TranscriptionError(DictateError):
    """Transcription pipeline failed."""


class QueueOverflowError(DictateError):
    """Transcription queue exceeded max depth."""


class PasteUnavailableError(DictateError):
    """Auto-paste backend unavailable on this platform."""
```

- [x] **Step 4: Run test; expect PASS**

```bash
.venv/bin/pytest tests/unit/test_errors.py -v
```

- [x] **Step 5: Commit**

```bash
git add dictate/errors.py tests/unit/test_errors.py
git commit -m "feat(errors): typed exceptions shared across modules"
```

---

### Task 4: config.py — defaults, TOML load/save, validation

**Files:**
- Create: `dictate/config.py`
- Test: `tests/unit/test_config.py`

- [x] **Step 1: Write the failing tests**

```python
# tests/unit/test_config.py
from pathlib import Path
import pytest
from dictate.config import Config, load, save, DEFAULT_CONFIG_TOML


def test_defaults_roundtrip(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text(DEFAULT_CONFIG_TOML)
    cfg = load(path)
    assert cfg.hotkey.binding == "ctrl+shift+d"
    assert cfg.hotkey.mode == "hold"
    assert cfg.model.size == "small"
    assert cfg.transcription.max_seconds == 180
    assert cfg.history.limit == 100


def test_missing_file_writes_default_and_loads(tmp_path: Path):
    path = tmp_path / "config.toml"
    cfg = load(path)
    assert path.exists()
    assert cfg.hotkey.binding == "ctrl+shift+d"
    # Round-trip preserves content
    assert DEFAULT_CONFIG_TOML in path.read_text()


def test_bad_field_falls_back_to_default(tmp_path: Path, caplog):
    path = tmp_path / "config.toml"
    path.write_text("""
[hotkey]
binding = "ctrl+shift+d"
mode = "invalid_mode"
""")
    cfg = load(path)
    assert cfg.hotkey.mode == "hold"  # default
    assert any("invalid" in rec.message.lower() for rec in caplog.records)


def test_save_atomic_temp_plus_rename(tmp_path: Path):
    path = tmp_path / "config.toml"
    cfg = load(path)  # writes default
    cfg.hotkey.binding = "F9"
    save(cfg, path)
    assert "F9" in path.read_text()
    # no leftover temp file
    assert list(tmp_path.iterdir()) == [path]


def test_invalid_toml_falls_back_and_logs(tmp_path: Path, caplog):
    path = tmp_path / "config.toml"
    path.write_text("this is not = = valid toml [")
    cfg = load(path)
    assert cfg.hotkey.binding == "ctrl+shift+d"
    assert any("parse" in rec.message.lower() or "toml" in rec.message.lower() for rec in caplog.records)
```

- [x] **Step 2: Run tests — expect failure**

```bash
.venv/bin/pytest tests/unit/test_config.py -v
```

Expected: import error (module doesn't exist).

- [x] **Step 3: Implement `dictate/config.py`**

```python
"""Config schema, defaults, TOML load/save. Atomic writes; bad fields fall back with logs."""
from __future__ import annotations

import logging
import os
import tomllib
from dataclasses import dataclass, field, asdict
from pathlib import Path

log = logging.getLogger(__name__)


DEFAULT_CONFIG_TOML = """\
# dictate config — see `dictate tui` for an interactive editor.
# Daemon reloads this file on SIGHUP. Fields marked [restart] require
# `dictate` to be restarted.

[hotkey]
binding = "ctrl+shift+d"
mode = "hold"                # "hold" | "toggle"

[model]
size          = "small"      # "small" | "medium"             [restart]
device        = "auto"       # "auto" | "cpu" | "cuda"        [restart]
compute_type  = "auto"       # "auto" | "int8" | "float16" | "int8_float16"
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
_COMPUTE_TYPES = {"auto", "int8", "float16", "int8_float16"}
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
```

- [x] **Step 4: Run tests — expect PASS**

```bash
.venv/bin/pytest tests/unit/test_config.py -v
```

- [x] **Step 5: Commit**

```bash
git add dictate/config.py tests/unit/test_config.py docs/superpowers/plans/2026-04-18-cli-replaces-gui.md
git commit -m "feat(config): TOML load/save with defaults, validation, atomic writes"
```

---

### Task 5: state.py — PID, status.json, history.jsonl, atomic writes

**Files:**
- Create: `dictate/state.py`
- Test: `tests/unit/test_state.py`

- [x] **Step 1: Write the failing tests**

```python
# tests/unit/test_state.py
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
```

- [x] **Step 2: Run tests — expect import failure**

```bash
.venv/bin/pytest tests/unit/test_state.py -v
```

- [x] **Step 3: Implement `dictate/state.py`**

```python
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
```

- [x] **Step 4: Run tests — expect PASS**

```bash
.venv/bin/pytest tests/unit/test_state.py -v
```

- [x] **Step 5: Commit**

```bash
git add dictate/state.py tests/unit/test_state.py
git commit -m "feat(state): PID, status.json, history.jsonl with atomic writes + rotation"
```

---

### Task 6: log.py — rotating file logger

**Files:**
- Create: `dictate/log.py`
- Test: `tests/unit/test_log.py`

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_log.py
import logging
from pathlib import Path
from dictate.log import configure


def test_configure_writes_to_file(tmp_path: Path):
    log_path = tmp_path / "dictate.log"
    configure(log_path, level="info", max_size_mb=1)
    logger = logging.getLogger("dictate.test")
    logger.info("hello world")
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert log_path.exists()
    assert "hello world" in log_path.read_text()


def test_configure_respects_level(tmp_path: Path):
    log_path = tmp_path / "dictate.log"
    configure(log_path, level="warn", max_size_mb=1)
    logger = logging.getLogger("dictate.test")
    logger.info("info message")
    logger.warning("warning message")
    for handler in logging.getLogger().handlers:
        handler.flush()
    body = log_path.read_text()
    assert "warning message" in body
    assert "info message" not in body
```

- [x] **Step 2: Run — expect failure**

```bash
.venv/bin/pytest tests/unit/test_log.py -v
```

- [x] **Step 3: Implement `dictate/log.py`**

```python
"""Rotating file logger — configured once at daemon startup."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARNING,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


def configure(path: Path, level: str = "info", max_size_mb: int = 10) -> None:
    """Install a rotating file handler on the root logger. Idempotent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    # Remove previous handlers (tests call this repeatedly)
    for h in list(root.handlers):
        root.removeHandler(h)
        h.close()
    handler = RotatingFileHandler(
        str(path),
        maxBytes=max_size_mb * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(_LEVELS.get(level.lower(), logging.INFO))
```

- [x] **Step 4: Run — expect PASS**

```bash
.venv/bin/pytest tests/unit/test_log.py -v
```

- [x] **Step 5: Commit**

```bash
git add dictate/log.py tests/unit/test_log.py
git commit -m "feat(log): rotating file logger configured at startup"
```

---

## Phase 2 — Logic modules (testable without hardware)

### Task 7: hotkey.py — parsing + state machine (no pynput yet)

**Files:**
- Create: `dictate/hotkey.py`
- Test: `tests/unit/test_hotkey.py`

This task implements the pure logic (modifier parsing, mode state machine). Task 13 wires pynput in.

- [x] **Step 1: Write failing tests**

```python
# tests/unit/test_hotkey.py
import pytest
from dictate.hotkey import parse_binding, HotkeyState, Mode


def test_parse_binding_simple_key():
    keys = parse_binding("F9")
    assert keys == frozenset({"f9"})


def test_parse_binding_modifier_combo():
    keys = parse_binding("ctrl+shift+d")
    assert keys == frozenset({"ctrl", "shift", "d"})


def test_parse_binding_case_insensitive():
    assert parse_binding("Ctrl+Shift+D") == parse_binding("ctrl+shift+d")


def test_parse_binding_space_requires_modifier():
    with pytest.raises(ValueError):
        parse_binding("space")
    # with a modifier is fine
    assert parse_binding("ctrl+space") == frozenset({"ctrl", "space"})


def test_hold_mode_press_starts_release_stops():
    started = []
    stopped = []
    hs = HotkeyState(Mode.HOLD, on_start=lambda: started.append(1),
                                 on_stop=lambda: stopped.append(1))
    hs.on_combo_press()
    assert started == [1]
    assert stopped == []
    hs.on_combo_release()
    assert stopped == [1]


def test_hold_mode_double_press_no_double_start():
    started = []
    hs = HotkeyState(Mode.HOLD, on_start=lambda: started.append(1),
                                 on_stop=lambda: None)
    hs.on_combo_press()
    hs.on_combo_press()
    assert started == [1]


def test_toggle_mode_press_flips_state():
    started = []
    stopped = []
    hs = HotkeyState(Mode.TOGGLE, on_start=lambda: started.append(1),
                                   on_stop=lambda: stopped.append(1))
    hs.on_combo_press()
    assert started == [1] and stopped == []
    hs.on_combo_release()  # release is ignored in toggle mode
    assert stopped == []
    hs.on_combo_press()
    assert stopped == [1]


def test_external_toggle_works_regardless_of_mode():
    started = []
    stopped = []
    hs = HotkeyState(Mode.HOLD, on_start=lambda: started.append(1),
                                 on_stop=lambda: stopped.append(1))
    hs.external_toggle()
    assert started == [1]
    hs.external_toggle()
    assert stopped == [1]
```

- [x] **Step 2: Run — expect failure**

```bash
.venv/bin/pytest tests/unit/test_hotkey.py -v
```

- [x] **Step 3: Implement `dictate/hotkey.py`**

```python
"""Hotkey binding parser + mode state machine. pynput wiring lives in Task 13."""
from __future__ import annotations

import enum
from typing import Callable


_MODIFIERS = {"ctrl", "shift", "alt", "super", "cmd", "meta"}


class Mode(enum.Enum):
    HOLD = "hold"
    TOGGLE = "toggle"


def parse_binding(binding: str) -> frozenset[str]:
    """Parse 'ctrl+shift+d' into a normalized keyset. Bare space requires modifier."""
    parts = [p.strip().lower() for p in binding.split("+") if p.strip()]
    if not parts:
        raise ValueError(f"empty hotkey binding: {binding!r}")
    keys = frozenset(parts)
    non_mod = keys - _MODIFIERS
    if "space" in non_mod and not (keys & _MODIFIERS):
        raise ValueError("hotkey 'space' requires a modifier (e.g. ctrl+space)")
    return keys


class HotkeyState:
    """State machine for recording sessions. Callbacks fire from arbitrary threads."""

    def __init__(
        self,
        mode: Mode,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
    ):
        self.mode = mode
        self._on_start = on_start
        self._on_stop = on_stop
        self._recording = False

    @property
    def recording(self) -> bool:
        return self._recording

    def on_combo_press(self) -> None:
        if self.mode is Mode.HOLD:
            if not self._recording:
                self._start()
        else:  # TOGGLE
            if self._recording:
                self._stop()
            else:
                self._start()

    def on_combo_release(self) -> None:
        if self.mode is Mode.HOLD and self._recording:
            self._stop()
        # TOGGLE: ignore releases

    def external_toggle(self) -> None:
        """SIGUSR1 entry point. Flips state regardless of mode."""
        if self._recording:
            self._stop()
        else:
            self._start()

    def _start(self) -> None:
        self._recording = True
        self._on_start()

    def _stop(self) -> None:
        self._recording = False
        self._on_stop()
```

- [x] **Step 4: Run — expect PASS**

```bash
.venv/bin/pytest tests/unit/test_hotkey.py -v
```

- [x] **Step 5: Commit**

```bash
git add dictate/hotkey.py tests/unit/test_hotkey.py
git commit -m "feat(hotkey): binding parser + HOLD/TOGGLE state machine"
```

---

### Task 8: jobs.py — single-worker transcription queue

**Files:**
- Create: `dictate/jobs.py`
- Test: `tests/unit/test_jobs.py`

- [x] **Step 1: Write failing tests**

```python
# tests/unit/test_jobs.py
import threading
import time
import pytest
from dictate.jobs import TranscriptionQueue
from dictate.errors import QueueOverflowError


def test_enqueue_processes_in_order():
    processed = []
    done = threading.Event()

    def worker(item):
        processed.append(item)
        if len(processed) == 3:
            done.set()

    q = TranscriptionQueue(worker, max_depth=10)
    q.start()
    for i in range(3):
        q.enqueue(i)
    assert done.wait(timeout=2)
    q.stop()
    assert processed == [0, 1, 2]


def test_overflow_drops_oldest_raises():
    events = []
    unblock = threading.Event()

    def worker(item):
        unblock.wait()
        events.append(("done", item))

    q = TranscriptionQueue(worker, max_depth=2)
    q.start()
    q.enqueue("a")    # starts processing immediately
    # Wait for worker to pull 'a'
    time.sleep(0.1)
    q.enqueue("b")    # sits in queue
    q.enqueue("c")    # sits in queue, depth is now 2
    with pytest.raises(QueueOverflowError):
        q.enqueue("d")    # overflow — drops 'b', raises
    unblock.set()
    q.stop(timeout=2)
    # 'a', 'c', 'd' processed; 'b' dropped
    names = [n for _, n in events]
    assert "a" in names
    assert "c" in names
    assert "d" in names
    assert "b" not in names


def test_worker_exception_does_not_kill_thread():
    events = []

    def worker(item):
        if item == "boom":
            raise RuntimeError("nope")
        events.append(item)

    q = TranscriptionQueue(worker, max_depth=10)
    q.start()
    q.enqueue("boom")
    q.enqueue("ok")
    time.sleep(0.2)
    q.stop()
    assert events == ["ok"]


def test_stop_drains_with_deadline():
    processed = []

    def slow(item):
        time.sleep(0.05)
        processed.append(item)

    q = TranscriptionQueue(slow, max_depth=10)
    q.start()
    for i in range(3):
        q.enqueue(i)
    q.stop(timeout=2)
    assert processed == [0, 1, 2]
```

- [x] **Step 2: Run — expect failure**

```bash
.venv/bin/pytest tests/unit/test_jobs.py -v
```

- [x] **Step 3: Implement `dictate/jobs.py`**

```python
"""Single-worker transcription queue with overflow-drops-oldest semantics."""
from __future__ import annotations

import logging
import threading
from collections import deque
from typing import Any, Callable

from dictate.errors import QueueOverflowError

log = logging.getLogger(__name__)


class TranscriptionQueue:
    def __init__(self, worker: Callable[[Any], None], max_depth: int = 10):
        self._worker = worker
        self._max_depth = max_depth
        self._q: deque = deque()
        self._cv = threading.Condition()
        self._stopping = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="dictate-queue")
        self._thread.start()

    def enqueue(self, item: Any) -> None:
        overflowed = False
        with self._cv:
            if len(self._q) >= self._max_depth:
                self._q.popleft()
                overflowed = True
            self._q.append(item)
            self._cv.notify()
        if overflowed:
            raise QueueOverflowError(
                f"queue full (depth={self._max_depth}); oldest job dropped"
            )

    def depth(self) -> int:
        with self._cv:
            return len(self._q)

    def stop(self, timeout: float = 5.0) -> None:
        with self._cv:
            self._stopping = True
            self._cv.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def _run(self) -> None:
        while True:
            with self._cv:
                while not self._q and not self._stopping:
                    self._cv.wait()
                if not self._q and self._stopping:
                    return
                item = self._q.popleft()
            try:
                self._worker(item)
            except Exception:
                log.exception("queue worker raised on item=%r", item)
```

- [x] **Step 4: Run — expect PASS**

```bash
.venv/bin/pytest tests/unit/test_jobs.py -v
```

- [x] **Step 5: Commit**

```bash
git add dictate/jobs.py tests/unit/test_jobs.py
git commit -m "feat(jobs): single-worker transcription queue with overflow"
```

---

### Task 9: paste.py — platform dispatch

**Files:**
- Create: `dictate/paste.py`
- Test: `tests/unit/test_paste.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_paste.py
from unittest.mock import patch, MagicMock
import pytest
from dictate.paste import paste, select_backend, WaylandYdotoolBackend, PynputBackend
from dictate.errors import PasteUnavailableError


def test_select_backend_wayland_picks_ydotool():
    be = select_backend(session="wayland", platform="linux")
    assert isinstance(be, WaylandYdotoolBackend)


def test_select_backend_x11_picks_pynput():
    be = select_backend(session="x11", platform="linux")
    assert isinstance(be, PynputBackend)


def test_select_backend_macos_picks_pynput():
    be = select_backend(session="", platform="darwin")
    assert isinstance(be, PynputBackend)


def test_select_backend_windows_picks_pynput():
    be = select_backend(session="", platform="win32")
    assert isinstance(be, PynputBackend)


def test_paste_pynput_success_presses_ctrl_v():
    mock_kb = MagicMock()
    be = PynputBackend(keyboard=mock_kb)
    be.paste("ctrl+v")
    # press + release called for ctrl and v
    assert mock_kb.press.call_count == 2
    assert mock_kb.release.call_count == 2


def test_paste_wayland_shells_out_to_ydotool():
    with patch("dictate.paste.subprocess.run") as run:
        run.return_value.returncode = 0
        be = WaylandYdotoolBackend()
        be.paste("ctrl+v")
        args, _ = run.call_args
        assert args[0][0] == "ydotool"


def test_paste_wayland_missing_ydotool_raises_unavailable():
    with patch("dictate.paste.subprocess.run", side_effect=FileNotFoundError):
        be = WaylandYdotoolBackend()
        with pytest.raises(PasteUnavailableError):
            be.paste("ctrl+v")
```

- [ ] **Step 2: Run — expect failure**

```bash
.venv/bin/pytest tests/unit/test_paste.py -v
```

- [ ] **Step 3: Implement `dictate/paste.py`**

```python
"""Auto-paste: pynput on X11/mac/Win, ydotool shell-out on Wayland."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import Protocol

from dictate.errors import PasteUnavailableError

log = logging.getLogger(__name__)


class Backend(Protocol):
    def paste(self, shortcut: str) -> None: ...


class PynputBackend:
    """X11 / macOS / Windows. Uses pynput.keyboard."""

    def __init__(self, keyboard=None):
        if keyboard is None:
            from pynput.keyboard import Controller  # lazy import
            keyboard = Controller()
        self._kb = keyboard
        # Defer pynput.keyboard.Key import for testability
        from pynput.keyboard import Key
        self._Key = Key

    def paste(self, shortcut: str) -> None:
        keys = _parse_shortcut(shortcut, self._Key)
        try:
            for k in keys:
                self._kb.press(k)
            for k in reversed(keys):
                self._kb.release(k)
        except Exception as e:
            raise PasteUnavailableError(f"pynput paste failed: {e}") from e


class WaylandYdotoolBackend:
    """Wayland fallback — shells out to ydotool."""

    def paste(self, shortcut: str) -> None:
        # ydotool key syntax: "ctrl+v"
        try:
            r = subprocess.run(["ydotool", "key", shortcut],
                               capture_output=True, timeout=2)
        except FileNotFoundError as e:
            raise PasteUnavailableError("ydotool not installed") from e
        except subprocess.TimeoutExpired as e:
            raise PasteUnavailableError("ydotool timed out") from e
        if r.returncode != 0:
            raise PasteUnavailableError(
                f"ydotool failed: rc={r.returncode} stderr={r.stderr!r}"
            )


def _parse_shortcut(shortcut: str, Key):
    """'ctrl+v' → [Key.ctrl, 'v']. Modifier order preserved."""
    mod_map = {"ctrl": Key.ctrl, "shift": Key.shift, "alt": Key.alt,
               "super": Key.cmd, "cmd": Key.cmd, "meta": Key.cmd}
    out = []
    for part in shortcut.lower().split("+"):
        part = part.strip()
        out.append(mod_map.get(part, part))
    return out


def select_backend(session: str | None = None, platform: str | None = None) -> Backend:
    session = session or os.environ.get("XDG_SESSION_TYPE", "")
    platform = platform or sys.platform
    if platform == "linux" and session == "wayland":
        return WaylandYdotoolBackend()
    return PynputBackend()


def paste(shortcut: str) -> None:
    """Fire-and-forget simulated paste. Swallows PasteUnavailableError by logging."""
    try:
        select_backend().paste(shortcut)
    except PasteUnavailableError as e:
        log.warning("autopaste unavailable: %s — clipboard-only", e)
```

- [ ] **Step 4: Run — expect PASS**

```bash
.venv/bin/pytest tests/unit/test_paste.py -v
```

- [ ] **Step 5: Commit**

```bash
git add dictate/paste.py tests/unit/test_paste.py
git commit -m "feat(paste): platform dispatch — pynput on X11/mac/Win, ydotool on Wayland"
```

---

## Phase 3 — Hardware adapters

### Task 10: recorder.py — sounddevice microphone capture

**Files:**
- Create: `dictate/recorder.py`
- Test: `tests/unit/test_recorder.py`

- [ ] **Step 1: Write failing tests (mocked sounddevice)**

```python
# tests/unit/test_recorder.py
from unittest.mock import patch, MagicMock
import numpy as np
import pytest
from dictate.recorder import Recorder
from dictate.errors import AudioError


def test_start_then_stop_returns_concatenated_buffer():
    with patch("dictate.recorder.sd") as sd:
        stream = MagicMock()
        sd.InputStream.return_value = stream
        rec = Recorder()
        rec.start()
        # simulate 3 callbacks, each 1024 float32 frames
        cb = sd.InputStream.call_args.kwargs["callback"]
        cb(np.ones((1024, 1), dtype=np.float32), 1024, None, None)
        cb(np.ones((1024, 1), dtype=np.float32) * 2, 1024, None, None)
        cb(np.ones((1024, 1), dtype=np.float32) * 3, 1024, None, None)
        audio = rec.stop()
        assert audio.shape == (3072,)
        assert np.allclose(audio[:1024], 1.0)
        assert np.allclose(audio[2048:], 3.0)


def test_stop_without_start_returns_empty():
    with patch("dictate.recorder.sd"):
        rec = Recorder()
        audio = rec.stop()
        assert audio.size == 0


def test_start_failure_raises_audio_error():
    with patch("dictate.recorder.sd") as sd:
        sd.InputStream.side_effect = Exception("no device")
        rec = Recorder()
        with pytest.raises(AudioError):
            rec.start()
```

- [ ] **Step 2: Run — expect failure**

```bash
.venv/bin/pytest tests/unit/test_recorder.py -v
```

- [ ] **Step 3: Implement `dictate/recorder.py`**

```python
"""Microphone capture via sounddevice. Mono float32 @ 16 kHz."""
from __future__ import annotations

import logging
import threading
from typing import Optional

import numpy as np
import sounddevice as sd

from dictate.errors import AudioError

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000


class Recorder:
    def __init__(self, sample_rate: int = SAMPLE_RATE, mic: Optional[str] = None):
        self.sample_rate = sample_rate
        self.mic = mic or None
        self._stream = None
        self._buffers: list[np.ndarray] = []
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._stream is not None:
            return
        self._buffers = []
        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                device=self.mic if self.mic else None,
                callback=self._callback,
            )
            self._stream.start()
        except Exception as e:
            self._stream = None
            raise AudioError(f"microphone start failed: {e}") from e

    def _callback(self, indata, frames, time_info, status):
        if status:
            log.debug("recorder callback status: %s", status)
        with self._lock:
            self._buffers.append(np.array(indata[:, 0], copy=True))

    def stop(self) -> np.ndarray:
        if self._stream is None:
            return np.zeros(0, dtype=np.float32)
        try:
            self._stream.stop()
            self._stream.close()
        except Exception:
            log.exception("recorder stop failed")
        self._stream = None
        with self._lock:
            if not self._buffers:
                return np.zeros(0, dtype=np.float32)
            out = np.concatenate(self._buffers)
            self._buffers = []
            return out
```

- [ ] **Step 4: Run — expect PASS**

```bash
.venv/bin/pytest tests/unit/test_recorder.py -v
```

- [ ] **Step 5: Commit**

```bash
git add dictate/recorder.py tests/unit/test_recorder.py
git commit -m "feat(recorder): sounddevice mono 16 kHz capture"
```

---

### Task 11: transcriber.py — faster-whisper wrapper

**Files:**
- Create: `dictate/transcriber.py`
- Test: `tests/unit/test_transcriber.py`

- [ ] **Step 1: Write failing tests (mocked model)**

```python
# tests/unit/test_transcriber.py
from unittest.mock import patch, MagicMock
import numpy as np
from dictate.transcriber import Transcriber, TranscriptionResult


def test_transcribe_returns_result_struct():
    segments = [MagicMock(text=" hello ", avg_logprob=-0.1, no_speech_prob=0.1),
                MagicMock(text=" world", avg_logprob=-0.2, no_speech_prob=0.1)]
    info = MagicMock(language="en", duration=1.5)
    with patch("dictate.transcriber.WhisperModel") as WM:
        wm = MagicMock()
        wm.transcribe.return_value = (iter(segments), info)
        WM.return_value = wm
        t = Transcriber(size="small", device="cpu", compute_type="int8")
        result = t.transcribe(np.zeros(16000, dtype=np.float32))
    assert isinstance(result, TranscriptionResult)
    assert result.text == "hello world"
    assert result.language == "en"
    assert 0.0 <= result.confidence <= 1.0


def test_empty_audio_returns_empty_text():
    with patch("dictate.transcriber.WhisperModel"):
        t = Transcriber(size="small", device="cpu", compute_type="int8")
        result = t.transcribe(np.zeros(0, dtype=np.float32))
    assert result.text == ""
```

- [ ] **Step 2: Run — expect failure**

```bash
.venv/bin/pytest tests/unit/test_transcriber.py -v
```

- [ ] **Step 3: Implement `dictate/transcriber.py`**

```python
"""faster-whisper wrapper. Loads the model once at startup."""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    text: str
    duration_ms: int
    language: str
    confidence: float


def _resolve_compute_type(device: str, requested: str) -> str:
    if requested != "auto":
        return requested
    return "float16" if device == "cuda" else "int8"


class Transcriber:
    def __init__(
        self,
        size: str = "small",
        device: str = "auto",
        compute_type: str = "auto",
        cache_dir: Optional[Path] = None,
    ):
        from faster_whisper import WhisperModel  # lazy import (heavy)
        if device == "auto":
            try:
                import ctranslate2
                device = "cuda" if "cuda" in ctranslate2.get_supported_devices() else "cpu"
            except Exception:
                device = "cpu"
        compute_type = _resolve_compute_type(device, compute_type)
        log.info("loading whisper model size=%s device=%s compute_type=%s",
                 size, device, compute_type)
        self._model = WhisperModel(
            size,
            device=device,
            compute_type=compute_type,
            download_root=str(cache_dir) if cache_dir else None,
        )
        self.size = size
        self.device = device
        self.compute_type = compute_type

    def transcribe(self, audio: np.ndarray) -> TranscriptionResult:
        if audio.size == 0:
            return TranscriptionResult(text="", duration_ms=0,
                                       language="", confidence=0.0)
        t0 = time.perf_counter()
        segments_iter, info = self._model.transcribe(audio, beam_size=5)
        # Average avg_logprob across segments → confidence in [0, 1]
        texts: list[str] = []
        logprobs: list[float] = []
        for seg in segments_iter:
            texts.append(seg.text.strip())
            logprobs.append(float(getattr(seg, "avg_logprob", -1.0)))
        text = " ".join(t for t in texts if t).strip()
        confidence = float(math.exp(sum(logprobs) / len(logprobs))) if logprobs else 0.0
        confidence = max(0.0, min(1.0, confidence))
        return TranscriptionResult(
            text=text,
            duration_ms=int((time.perf_counter() - t0) * 1000),
            language=getattr(info, "language", ""),
            confidence=confidence,
        )
```

- [ ] **Step 4: Run — expect PASS**

```bash
.venv/bin/pytest tests/unit/test_transcriber.py -v
```

- [ ] **Step 5: Commit**

```bash
git add dictate/transcriber.py tests/unit/test_transcriber.py
git commit -m "feat(transcriber): faster-whisper wrapper with auto device/compute"
```

---

### Task 12: clipboard.py — pyperclip wrapper

**Files:**
- Create: `dictate/clipboard.py`
- Test: `tests/unit/test_clipboard.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_clipboard.py
from unittest.mock import patch
from dictate.clipboard import copy


def test_copy_calls_pyperclip():
    with patch("dictate.clipboard.pyperclip") as pc:
        copy("hello")
        pc.copy.assert_called_once_with("hello")


def test_copy_swallows_pyperclip_exception(caplog):
    import pyperclip
    with patch("dictate.clipboard.pyperclip") as pc:
        pc.copy.side_effect = pyperclip.PyperclipException("no backend")
        copy("hello")  # must not raise
    assert any("clipboard" in rec.message.lower() for rec in caplog.records)
```

- [ ] **Step 2: Run — expect failure**

```bash
.venv/bin/pytest tests/unit/test_clipboard.py -v
```

- [ ] **Step 3: Implement `dictate/clipboard.py`**

```python
"""Clipboard writes via pyperclip. Failures log and return."""
from __future__ import annotations

import logging

import pyperclip

log = logging.getLogger(__name__)


def copy(text: str) -> None:
    try:
        pyperclip.copy(text)
    except pyperclip.PyperclipException as e:
        log.warning("clipboard write failed: %s", e)
```

- [ ] **Step 4: Run — expect PASS**

```bash
.venv/bin/pytest tests/unit/test_clipboard.py -v
```

- [ ] **Step 5: Commit**

```bash
git add dictate/clipboard.py tests/unit/test_clipboard.py
git commit -m "feat(clipboard): pyperclip wrapper with graceful failure"
```

---

## Phase 4 — Hotkey integration

### Task 13: Wire pynput listener to HotkeyState

**Files:**
- Modify: `dictate/hotkey.py` (add `HotkeyListener`)
- Test: `tests/unit/test_hotkey_listener.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_hotkey_listener.py
from unittest.mock import MagicMock, patch
from dictate.hotkey import HotkeyListener, Mode


def test_listener_starts_and_stops():
    with patch("dictate.hotkey.keyboard") as kb:
        listener_instance = MagicMock()
        kb.Listener.return_value = listener_instance
        hl = HotkeyListener("ctrl+shift+d", Mode.HOLD,
                            on_start=lambda: None, on_stop=lambda: None)
        hl.start()
        listener_instance.start.assert_called_once()
        hl.stop()
        listener_instance.stop.assert_called_once()


def test_listener_press_release_drives_state_machine():
    with patch("dictate.hotkey.keyboard") as kb:
        events = []
        kb.Listener.return_value = MagicMock()
        hl = HotkeyListener("ctrl+shift+d", Mode.HOLD,
                            on_start=lambda: events.append("start"),
                            on_stop=lambda: events.append("stop"))
        # Simulate the full combo being held
        hl._on_press(_make_key(kb, "ctrl"))
        hl._on_press(_make_key(kb, "shift"))
        hl._on_press(_make_key(kb, "d"))
        assert events == ["start"]
        hl._on_release(_make_key(kb, "d"))
        assert events == ["start", "stop"]


def _make_key(kb_mock, name):
    """Fake a pynput.keyboard.KeyCode or Key with our naming."""
    k = MagicMock()
    k.char = None
    # Exploit the name resolution in _key_name
    if name in {"ctrl", "shift", "alt", "super", "cmd", "meta"}:
        k.name = name
    else:
        k.char = name
    return k
```

- [ ] **Step 2: Run — expect failure**

```bash
.venv/bin/pytest tests/unit/test_hotkey_listener.py -v
```

- [ ] **Step 3: Extend `dictate/hotkey.py` with `HotkeyListener`**

Append below the `HotkeyState` class:

```python
# --- pynput wiring -----------------------------------------------------------

try:
    from pynput import keyboard  # type: ignore
except Exception:  # pragma: no cover — env without display
    keyboard = None


_KEY_ALIASES = {
    "ctrl_l": "ctrl", "ctrl_r": "ctrl",
    "shift_l": "shift", "shift_r": "shift",
    "alt_l": "alt", "alt_r": "alt", "alt_gr": "alt",
    "cmd_l": "cmd", "cmd_r": "cmd", "cmd": "cmd",
}


def _key_name(key) -> str | None:
    """Normalize a pynput key/keycode to the names used in parse_binding."""
    # KeyCode (printable)
    char = getattr(key, "char", None)
    if char:
        return char.lower()
    name = getattr(key, "name", None)
    if not name:
        return None
    return _KEY_ALIASES.get(name.lower(), name.lower())


class HotkeyListener:
    """Listens for the configured combo using pynput; drives HotkeyState."""

    def __init__(self, binding: str, mode: Mode,
                 on_start, on_stop):
        self._target = parse_binding(binding)
        self._state = HotkeyState(mode, on_start=on_start, on_stop=on_stop)
        self._pressed: set[str] = set()
        self._combo_active = False
        self._listener = None

    def start(self) -> None:
        if keyboard is None:
            raise RuntimeError("pynput.keyboard unavailable")
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    def external_toggle(self) -> None:
        self._state.external_toggle()

    def _on_press(self, key):
        name = _key_name(key)
        if name is None:
            return
        self._pressed.add(name)
        if not self._combo_active and self._target.issubset(self._pressed):
            self._combo_active = True
            self._state.on_combo_press()

    def _on_release(self, key):
        name = _key_name(key)
        if name is None:
            return
        self._pressed.discard(name)
        if self._combo_active and not self._target.issubset(self._pressed):
            self._combo_active = False
            self._state.on_combo_release()
```

- [ ] **Step 4: Run — expect PASS**

```bash
.venv/bin/pytest tests/unit/test_hotkey_listener.py -v
```

- [ ] **Step 5: Commit**

```bash
git add dictate/hotkey.py tests/unit/test_hotkey_listener.py
git commit -m "feat(hotkey): pynput listener drives HotkeyState machine"
```

---

## Phase 5 — Daemon + CLI

### Task 14: daemon.py — main loop, signal handlers, orchestration

**Files:**
- Create: `dictate/daemon.py`, `dictate/paths.py`
- Test: `tests/unit/test_daemon.py`

- [ ] **Step 1: Implement `dictate/paths.py` (XDG helpers)**

```python
# dictate/paths.py
"""XDG path helpers."""
from __future__ import annotations

import os
from pathlib import Path


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "dictate"


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "dictate"


def data_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "dictate"


def config_path() -> Path:
    return config_dir() / "config.toml"


def log_path() -> Path:
    return data_dir() / "dictate.log"
```

- [ ] **Step 2: Write failing test for the daemon orchestration**

```python
# tests/unit/test_daemon.py
"""We test the daemon's orchestration in isolation by mocking its hardware-facing
components. Full integration tests live in tests/integration."""
from unittest.mock import MagicMock, patch
from pathlib import Path
from dictate.config import Config


def test_daemon_wires_components_and_writes_pid(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    with patch("dictate.daemon.Transcriber") as T, \
         patch("dictate.daemon.Recorder") as R, \
         patch("dictate.daemon.HotkeyListener") as HK:
        from dictate.daemon import Daemon
        d = Daemon(cfg=Config())
        d.setup()
        pid_file = tmp_path / "cache" / "dictate" / "dictate.pid"
        assert pid_file.exists()
        T.assert_called_once()
        R.assert_called_once()
        HK.assert_called_once()


def test_sigusr1_forwards_to_external_toggle(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    with patch("dictate.daemon.Transcriber"), \
         patch("dictate.daemon.Recorder"), \
         patch("dictate.daemon.HotkeyListener") as HK:
        hk_instance = MagicMock()
        HK.return_value = hk_instance
        from dictate.daemon import Daemon
        d = Daemon(cfg=Config())
        d.setup()
        d._handle_sigusr1(0, None)
        hk_instance.external_toggle.assert_called_once()
```

- [ ] **Step 3: Run — expect failure**

```bash
.venv/bin/pytest tests/unit/test_daemon.py -v
```

- [ ] **Step 4: Implement `dictate/daemon.py`**

```python
"""Daemon: model load, hotkey listener, queue, signal handlers. Foreground process."""
from __future__ import annotations

import datetime as dt
import logging
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from dictate import clipboard, log, paste, paths
from dictate.config import Config, load as load_config
from dictate.errors import DictateError
from dictate.hotkey import HotkeyListener, Mode
from dictate.jobs import TranscriptionQueue
from dictate.recorder import Recorder
from dictate.state import HistoryEntry, StateWriter, StatusSnapshot
from dictate.transcriber import Transcriber, TranscriptionResult


class Daemon:
    def __init__(self, cfg: Optional[Config] = None):
        self._cfg = cfg if cfg is not None else load_config(paths.config_path())
        self._state = StateWriter(
            cache_dir=paths.cache_dir(),
            data_dir=paths.data_dir(),
            history_limit=self._cfg.history.limit,
        )
        self._transcriber: Optional[Transcriber] = None
        self._recorder: Optional[Recorder] = None
        self._hotkey: Optional[HotkeyListener] = None
        self._queue: Optional[TranscriptionQueue] = None
        self._stop_event = threading.Event()
        self._needs_restart = False
        self._last_error: Optional[str] = None

    # --- lifecycle ----------------------------------------------------------

    def setup(self) -> None:
        log.configure(paths.log_path(),
                      level=self._cfg.logs.level,
                      max_size_mb=self._cfg.logs.max_size_mb)
        logging.getLogger("dictate").info("daemon starting")
        self._state.write_pid()
        self._install_signal_handlers()

        self._transcriber = Transcriber(
            size=self._cfg.model.size,
            device=self._cfg.model.device,
            compute_type=self._cfg.model.compute_type,
            cache_dir=Path(self._cfg.model.cache_dir) if self._cfg.model.cache_dir else None,
        )
        self._recorder = Recorder(mic=self._cfg.audio.microphone or None)
        self._queue = TranscriptionQueue(self._process_audio, max_depth=10)
        self._hotkey = HotkeyListener(
            binding=self._cfg.hotkey.binding,
            mode=Mode(self._cfg.hotkey.mode),
            on_start=self._start_recording,
            on_stop=self._stop_recording,
        )
        self._write_status("idle")

    def run(self) -> int:
        self.setup()
        self._queue.start()
        self._hotkey.start()
        try:
            while not self._stop_event.is_set():
                self._write_status(self._derive_state())
                self._stop_event.wait(0.2)
            return 0
        finally:
            self._shutdown()

    # --- signal handlers ----------------------------------------------------

    def _install_signal_handlers(self) -> None:
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        signal.signal(signal.SIGINT, self._handle_sigterm)
        signal.signal(signal.SIGHUP, self._handle_sighup)
        signal.signal(signal.SIGUSR1, self._handle_sigusr1)

    def _handle_sigterm(self, signum, frame) -> None:
        logging.getLogger("dictate").info("SIGTERM/SIGINT received — shutting down")
        self._stop_event.set()

    def _handle_sighup(self, signum, frame) -> None:
        logging.getLogger("dictate").info("SIGHUP — reloading config")
        try:
            new_cfg = load_config(paths.config_path())
        except DictateError as e:
            self._last_error = f"config reload failed: {e}"
            return
        needs_restart = self._structural_change(self._cfg, new_cfg)
        self._cfg = new_cfg
        if needs_restart:
            self._needs_restart = True
            logging.getLogger("dictate").warning(
                "structural config change — restart required"
            )

    def _handle_sigusr1(self, signum, frame) -> None:
        if self._hotkey:
            self._hotkey.external_toggle()

    @staticmethod
    def _structural_change(old: Config, new: Config) -> bool:
        return (
            old.model.size != new.model.size
            or old.model.device != new.model.device
            or old.model.compute_type != new.model.compute_type
            or old.model.cache_dir != new.model.cache_dir
            or old.audio.microphone != new.audio.microphone
        )

    # --- recording + transcription -----------------------------------------

    def _start_recording(self) -> None:
        try:
            self._recorder.start()
        except DictateError as e:
            self._last_error = str(e)

    def _stop_recording(self) -> None:
        audio = self._recorder.stop()
        if audio.size == 0:
            return
        try:
            self._queue.enqueue(audio)
        except DictateError as e:
            self._last_error = str(e)

    def _process_audio(self, audio) -> None:
        try:
            result: TranscriptionResult = self._transcriber.transcribe(audio)
        except Exception as e:
            self._last_error = f"transcription failed: {e}"
            logging.getLogger("dictate").exception("transcription failed")
            return
        if not result.text:
            return
        clipboard.copy(result.text)
        if self._cfg.transcription.autopaste:
            paste.paste(self._cfg.transcription.paste_shortcut)
        if self._cfg.history.save:
            self._state.append_history(HistoryEntry(
                ts=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                text=result.text,
                duration_ms=result.duration_ms,
                language=result.language,
                confidence=result.confidence,
            ))

    # --- status -------------------------------------------------------------

    def _derive_state(self) -> str:
        if self._last_error:
            return "error"
        if self._hotkey and self._hotkey._state.recording:
            return "recording"
        if self._queue and self._queue.depth() > 0:
            return "transcribing"
        return "idle"

    def _write_status(self, state: str) -> None:
        import os as _os
        snap = StatusSnapshot(
            state=state,
            recording=bool(self._hotkey and self._hotkey._state.recording),
            queue_depth=self._queue.depth() if self._queue else 0,
            last_error=self._last_error,
            pid=_os.getpid(),
            uptime_s=self._state.uptime_s(),
            model_loaded=self._transcriber is not None,
            needs_restart=self._needs_restart,
        )
        self._state.write_status(snap)

    # --- shutdown -----------------------------------------------------------

    def _shutdown(self) -> None:
        logging.getLogger("dictate").info("daemon shutting down")
        if self._hotkey:
            self._hotkey.stop()
        if self._queue:
            self._queue.stop(timeout=5.0)
        self._state.clear_pid()


def main() -> int:
    return Daemon().run()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run — expect PASS**

```bash
.venv/bin/pytest tests/unit/test_daemon.py -v
```

- [ ] **Step 6: Commit**

```bash
git add dictate/daemon.py dictate/paths.py tests/unit/test_daemon.py
git commit -m "feat(daemon): main loop, signal handlers, transcription orchestration"
```

---

### Task 15: cli.py — subcommand dispatch

**Files:**
- Create: `dictate/cli.py`, `dictate/__main__.py`
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_cli.py
import os
import signal
from pathlib import Path
from unittest.mock import patch
from dictate.cli import main


def test_dictate_no_args_runs_daemon():
    with patch("dictate.cli.Daemon") as D:
        D.return_value.run.return_value = 0
        rc = main([])
        assert rc == 0
        D.return_value.run.assert_called_once()


def test_dictate_version(capsys):
    rc = main(["--version"])
    captured = capsys.readouterr()
    from dictate import __version__
    assert __version__ in captured.out
    assert rc == 0


def test_dictate_toggle_sends_sigusr1(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    pid_dir = tmp_path / "dictate"
    pid_dir.mkdir()
    pid_file = pid_dir / "dictate.pid"
    pid_file.write_text(f"{os.getpid()}\n{int(0)}\n")
    with patch("dictate.cli.os.kill") as k:
        rc = main(["toggle"])
        k.assert_called_once_with(os.getpid(), signal.SIGUSR1)
        assert rc == 0


def test_dictate_toggle_no_daemon_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    rc = main(["toggle"])
    captured = capsys.readouterr()
    assert rc != 0
    assert "no" in captured.err.lower() and "daemon" in captured.err.lower()


def test_dictate_tui_no_daemon_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    rc = main(["tui"])
    captured = capsys.readouterr()
    assert rc != 0
    assert "no" in captured.err.lower() and "daemon" in captured.err.lower()
```

- [ ] **Step 2: Run — expect failure**

```bash
.venv/bin/pytest tests/unit/test_cli.py -v
```

- [ ] **Step 3: Implement `dictate/cli.py`**

```python
"""CLI dispatch. `dictate` alone = daemon; subcommands for TUI, signals."""
from __future__ import annotations

import argparse
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from dictate import __version__, paths
from dictate.daemon import Daemon


def _read_pid() -> Optional[int]:
    pid_path = paths.cache_dir() / "dictate.pid"
    if not pid_path.exists():
        return None
    try:
        pid = int(pid_path.read_text().splitlines()[0])
    except (ValueError, IndexError):
        return None
    # Is the process still alive?
    try:
        os.kill(pid, 0)
    except OSError:
        return None
    return pid


def _signal_daemon(sig: int) -> int:
    pid = _read_pid()
    if pid is None:
        print("no dictate daemon running. start one with 'dictate' in another terminal.",
              file=sys.stderr)
        return 1
    try:
        os.kill(pid, sig)
    except OSError as e:
        print(f"failed to signal daemon (pid={pid}): {e}", file=sys.stderr)
        return 1
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="dictate", description="Offline speech-to-text.")
    parser.add_argument("--version", action="store_true")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("tui", help="Launch the Textual TUI (requires a running daemon).")
    sub.add_parser("toggle", help="Send toggle (SIGUSR1) to the running daemon.")
    sub.add_parser("start", help="Send start signal (SIGUSR1) — Sway press bindings.")
    sub.add_parser("stop", help="Send stop signal (SIGUSR1) — Sway release bindings.")

    args = parser.parse_args(argv)

    if args.version:
        print(f"dictate {__version__}")
        return 0

    if args.cmd is None:
        return Daemon().run()
    if args.cmd == "tui":
        if _read_pid() is None:
            print("no dictate daemon running. start one with 'dictate' in another terminal, "
                  "or see README for systemd setup.", file=sys.stderr)
            return 1
        from dictate.tui.app import run_tui
        return run_tui()
    if args.cmd in {"toggle", "start", "stop"}:
        return _signal_daemon(signal.SIGUSR1)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Write `dictate/__main__.py`**

```python
"""Allow `python -m dictate` as a daemon alias."""
from dictate.cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Stub `dictate/tui/app.py` for CLI import** (fully implemented in Task 16)

```python
# dictate/tui/app.py
def run_tui() -> int:
    raise NotImplementedError("TUI implemented in Task 16+")
```

- [ ] **Step 6: Run tests — expect PASS**

```bash
.venv/bin/pytest tests/unit/test_cli.py -v
```

- [ ] **Step 7: Commit**

```bash
git add dictate/cli.py dictate/__main__.py dictate/tui/app.py tests/unit/test_cli.py
git commit -m "feat(cli): subcommand dispatch (daemon default, tui, toggle/start/stop)"
```

---

## Phase 6 — TUI

### Task 16: tui/app.py — skeleton, footer, routing

**Files:**
- Modify: `dictate/tui/app.py`
- Create: `dictate/tui/footer.py`
- Test: `tests/tui/test_app.py`

- [ ] **Step 1: Write failing test**

```python
# tests/tui/test_app.py
import json
from pathlib import Path

import pytest

from dictate.tui.app import DictateTUI


@pytest.mark.asyncio
async def test_footer_renders_status(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    status_dir = tmp_path / "dictate"
    status_dir.mkdir()
    (status_dir / "status.json").write_text(json.dumps({
        "state": "idle", "recording": False, "queue_depth": 0,
        "last_error": None, "pid": 1234, "uptime_s": 5,
        "model_loaded": True, "needs_restart": False,
    }))
    app = DictateTUI()
    async with app.run_test() as pilot:
        await pilot.pause()
        rendered = app.query_one("#status-footer").render().plain
        assert "idle" in rendered.lower()


@pytest.mark.asyncio
async def test_sidebar_navigation(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    app = DictateTUI()
    async with app.run_test() as pilot:
        await pilot.press("s")
        assert app.current_screen_name == "settings"
        await pilot.press("h")
        assert app.current_screen_name == "history"
```

- [ ] **Step 2: Run — expect failure**

```bash
.venv/bin/pytest tests/tui/test_app.py -v
```

- [ ] **Step 3: Implement `dictate/tui/footer.py`**

```python
# dictate/tui/footer.py
"""Live status footer — polls status.json at 10 Hz."""
from __future__ import annotations

import json
from pathlib import Path

from textual.widgets import Static

from dictate import paths


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
```

- [ ] **Step 4: Implement `dictate/tui/app.py`**

```python
"""Textual app root. Three screens: Status, Settings, History."""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Static, ListView, ListItem, Label

from dictate.tui.footer import StatusFooter


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
            yield Vertical(Static("Welcome — press s for Settings, h for History.",
                                  id="content-static"), id="content")
        yield StatusFooter(id="status-footer")

    def action_jump(self, name: str) -> None:
        self.current_screen_name = name
        content = self.query_one("#content-static", Static)
        content.update(f"(screen: {name})")
        # Real screen implementations in Task 17-19 replace this


def run_tui() -> int:
    DictateTUI().run()
    return 0
```

- [ ] **Step 5: Run — expect PASS**

```bash
.venv/bin/pytest tests/tui/test_app.py -v
```

- [ ] **Step 6: Commit**

```bash
git add dictate/tui/app.py dictate/tui/footer.py tests/tui/test_app.py
git commit -m "feat(tui): app skeleton with sidebar navigation and live footer"
```

---

### Task 17: tui/status.py — Status screen

**Files:**
- Create: `dictate/tui/status.py`
- Modify: `dictate/tui/app.py`
- Test: `tests/tui/test_status_screen.py`

- [ ] **Step 1: Write failing test**

```python
# tests/tui/test_status_screen.py
import json
from pathlib import Path

import pytest

from dictate.tui.app import DictateTUI


@pytest.mark.asyncio
async def test_status_screen_renders_state_fields(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    sd = tmp_path / "dictate"
    sd.mkdir()
    (sd / "status.json").write_text(json.dumps({
        "state": "recording", "recording": True, "queue_depth": 1,
        "last_error": None, "pid": 7, "uptime_s": 100,
        "model_loaded": True, "needs_restart": False,
    }))
    app = DictateTUI()
    async with app.run_test() as pilot:
        await pilot.pause()
        # Default screen is status
        state_widget = app.query_one("#status-state")
        assert "recording" in state_widget.render().plain.lower()
```

- [ ] **Step 2: Run — expect failure**

```bash
.venv/bin/pytest tests/tui/test_status_screen.py -v
```

- [ ] **Step 3: Implement `dictate/tui/status.py`**

```python
# dictate/tui/status.py
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
```

- [ ] **Step 4: Wire `StatusScreen` into `DictateTUI`**

Replace the `action_jump` method in `dictate/tui/app.py` with screen mounting, and change `compose` to mount the status screen by default:

```python
    # Replace the old content block inside compose():
        with Horizontal(id="body"):
            yield Sidebar(
                ListItem(Label("Status"), id="nav-status"),
                ListItem(Label("Settings"), id="nav-settings"),
                ListItem(Label("History"), id="nav-history"),
            )
            yield Vertical(StatusScreen(id="screen-body"), id="content")

    # Replace action_jump:
    def action_jump(self, name: str) -> None:
        self.current_screen_name = name
        content = self.query_one("#content")
        content.remove_children()
        if name == "status":
            content.mount(StatusScreen(id="screen-body"))
        elif name == "settings":
            from dictate.tui.settings import SettingsScreen
            content.mount(SettingsScreen(id="screen-body"))
        elif name == "history":
            from dictate.tui.history import HistoryScreen
            content.mount(HistoryScreen(id="screen-body"))
```

Add the import at the top of `dictate/tui/app.py`:

```python
from dictate.tui.status import StatusScreen
```

- [ ] **Step 5: Run — expect PASS**

```bash
.venv/bin/pytest tests/tui/test_status_screen.py tests/tui/test_app.py -v
```

- [ ] **Step 6: Commit**

```bash
git add dictate/tui/status.py dictate/tui/app.py tests/tui/test_status_screen.py
git commit -m "feat(tui): Status screen with live state/pid/uptime/queue"
```

---

### Task 18: tui/settings.py — Settings screen with save bar

**Files:**
- Create: `dictate/tui/settings.py`
- Test: `tests/tui/test_settings_screen.py`

- [ ] **Step 1: Write failing test**

```python
# tests/tui/test_settings_screen.py
import os
import signal
from pathlib import Path
from unittest.mock import patch

import pytest

from dictate.tui.app import DictateTUI


@pytest.mark.asyncio
async def test_settings_edit_and_save_sends_sighup(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    # pretend a daemon is running at our own pid so `os.kill(pid, 0)` passes
    pid_dir = tmp_path / "cache" / "dictate"
    pid_dir.mkdir(parents=True)
    (pid_dir / "dictate.pid").write_text(f"{os.getpid()}\n0\n")

    app = DictateTUI()
    async with app.run_test() as pilot:
        await pilot.press("s")  # settings screen
        # Change the hotkey binding field
        await pilot.click("#field-hotkey-binding")
        await pilot.press("backspace") * 20  # clear existing
        await pilot.type("F9")
        with patch("dictate.tui.settings.os.kill") as kill:
            await pilot.press("ctrl+s")
            kill.assert_called_once()
            assert kill.call_args[0][1] == signal.SIGHUP
        cfg_path = tmp_path / "config" / "dictate" / "config.toml"
        assert "F9" in cfg_path.read_text()
```

- [ ] **Step 2: Run — expect failure**

```bash
.venv/bin/pytest tests/tui/test_settings_screen.py -v
```

- [ ] **Step 3: Implement `dictate/tui/settings.py`**

```python
# dictate/tui/settings.py
"""Settings screen — flat form, explicit Save (Ctrl+S)."""
from __future__ import annotations

import os
import signal
from dataclasses import fields
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
```

- [ ] **Step 4: Run — expect PASS**

```bash
.venv/bin/pytest tests/tui/test_settings_screen.py -v
```

- [ ] **Step 5: Commit**

```bash
git add dictate/tui/settings.py tests/tui/test_settings_screen.py
git commit -m "feat(tui): Settings screen with flat form and Ctrl+S save → SIGHUP"
```

---

### Task 19: tui/history.py — History screen

**Files:**
- Create: `dictate/tui/history.py`
- Test: `tests/tui/test_history_screen.py`

- [ ] **Step 1: Write failing test**

```python
# tests/tui/test_history_screen.py
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
```

- [ ] **Step 2: Run — expect failure**

```bash
.venv/bin/pytest tests/tui/test_history_screen.py -v
```

- [ ] **Step 3: Implement `dictate/tui/history.py`**

```python
# dictate/tui/history.py
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
```

- [ ] **Step 4: Run — expect PASS**

```bash
.venv/bin/pytest tests/tui/test_history_screen.py -v
```

- [ ] **Step 5: Commit**

```bash
git add dictate/tui/history.py tests/tui/test_history_screen.py
git commit -m "feat(tui): History screen grouped by day"
```

---

## Phase 7 — Integration tests + CI

### Task 20: Subprocess integration tests (signals, PID lifecycle)

**Files:**
- Create: `tests/integration/test_daemon_subprocess.py`, `tests/integration/conftest.py`

- [ ] **Step 1: Write `tests/integration/conftest.py`**

```python
# tests/integration/conftest.py
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest


@pytest.fixture
def dictate_env(tmp_path: Path):
    """Isolate XDG dirs so the test daemon doesn't touch user state."""
    env = os.environ.copy()
    env["XDG_CONFIG_HOME"] = str(tmp_path / "config")
    env["XDG_CACHE_HOME"] = str(tmp_path / "cache")
    env["XDG_DATA_HOME"] = str(tmp_path / "data")
    yield env


@pytest.fixture
def spawn_daemon(dictate_env, monkeypatch):
    """Launch the daemon as a subprocess with heavy components stubbed out.

    The subprocess loads a small monkey-patch module first that replaces
    Transcriber / Recorder / HotkeyListener with fakes.
    """
    stub_path = Path(__file__).parent / "_stub_daemon.py"
    proc = subprocess.Popen(
        [sys.executable, str(stub_path)],
        env=dictate_env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    # wait for PID file to appear (up to 5s)
    pid_file = Path(dictate_env["XDG_CACHE_HOME"]) / "dictate" / "dictate.pid"
    for _ in range(50):
        if pid_file.exists():
            break
        time.sleep(0.1)
    else:
        proc.kill()
        out, err = proc.communicate(timeout=2)
        raise RuntimeError(f"daemon did not start: stdout={out!r} stderr={err!r}")
    yield proc, pid_file
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
```

- [ ] **Step 2: Write stub daemon `tests/integration/_stub_daemon.py`**

```python
# tests/integration/_stub_daemon.py
"""Run Daemon with hardware components stubbed — used by integration tests."""
import sys
from unittest.mock import MagicMock

from dictate import daemon as D

# Replace hardware components with MagicMocks
D.Transcriber = lambda *a, **kw: MagicMock()
D.Recorder = lambda *a, **kw: MagicMock(start=lambda: None,
                                        stop=lambda: __import__("numpy").zeros(0))
# Keep HotkeyListener but skip pynput:
original = D.HotkeyListener


class FakeHL:
    def __init__(self, binding, mode, on_start, on_stop):
        self._state = MagicMock(recording=False)
        self.on_start, self.on_stop = on_start, on_stop
    def start(self): pass
    def stop(self): pass
    def external_toggle(self):
        self._state.recording = not self._state.recording
        (self.on_stop if not self._state.recording else self.on_start)()


D.HotkeyListener = FakeHL

sys.exit(D.main())
```

- [ ] **Step 3: Write failing integration tests**

```python
# tests/integration/test_daemon_subprocess.py
import json
import os
import signal
import time
from pathlib import Path


def _wait_status(cache_home: Path, predicate, timeout=5.0):
    path = Path(cache_home) / "dictate" / "status.json"
    start = time.time()
    while time.time() - start < timeout:
        if path.exists():
            try:
                data = json.loads(path.read_text())
                if predicate(data):
                    return data
            except Exception:
                pass
        time.sleep(0.1)
    raise AssertionError(f"status predicate never matched; last: {path.read_text() if path.exists() else None}")


def test_daemon_writes_pid_and_status(spawn_daemon, dictate_env):
    proc, pid_file = spawn_daemon
    assert pid_file.exists()
    pid_txt = pid_file.read_text().strip()
    assert int(pid_txt.splitlines()[0]) == proc.pid
    data = _wait_status(dictate_env["XDG_CACHE_HOME"], lambda d: d["state"] == "idle")
    assert data["pid"] == proc.pid


def test_sighup_reloads_config(spawn_daemon, dictate_env):
    proc, _ = spawn_daemon
    cfg_path = Path(dictate_env["XDG_CONFIG_HOME"]) / "dictate" / "config.toml"
    body = cfg_path.read_text()
    cfg_path.write_text(body.replace('verbose_metadata = false', 'verbose_metadata = true'))
    os.kill(proc.pid, signal.SIGHUP)
    time.sleep(0.3)
    # Process should still be alive
    assert proc.poll() is None


def test_sigterm_clean_exit_removes_pid(spawn_daemon, dictate_env):
    proc, pid_file = spawn_daemon
    os.kill(proc.pid, signal.SIGTERM)
    proc.wait(timeout=5)
    assert proc.returncode == 0
    assert not pid_file.exists()


def test_sigusr1_flips_recording_state(spawn_daemon, dictate_env):
    proc, _ = spawn_daemon
    _wait_status(dictate_env["XDG_CACHE_HOME"], lambda d: d["state"] == "idle")
    os.kill(proc.pid, signal.SIGUSR1)
    _wait_status(dictate_env["XDG_CACHE_HOME"], lambda d: d["recording"] is True, timeout=2)
    os.kill(proc.pid, signal.SIGUSR1)
    _wait_status(dictate_env["XDG_CACHE_HOME"], lambda d: d["recording"] is False, timeout=2)
```

- [ ] **Step 4: Run — expect PASS**

```bash
.venv/bin/pytest tests/integration -v
```

- [ ] **Step 5: Commit**

```bash
git add tests/integration
git commit -m "test(integration): subprocess tests for PID, SIGHUP, SIGTERM, SIGUSR1"
```

---

### Task 21: GitHub Actions CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main, "rebuild/**"]
  pull_request:

jobs:
  unit:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install portaudio (Linux)
        if: runner.os == 'Linux'
        run: sudo apt-get update && sudo apt-get install -y libportaudio2
      - name: Install portaudio (macOS)
        if: runner.os == 'macOS'
        run: brew install portaudio
      - run: python -m pip install -U pip
      - run: python -m pip install -e .[dev]
      - run: python -m pytest tests/unit tests/tui -v

  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: sudo apt-get update && sudo apt-get install -y libportaudio2
      - run: python -m pip install -U pip
      - run: python -m pip install -e .[dev]
      - run: python -m pytest tests/integration -v
```

- [ ] **Step 2: Verify YAML parses**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```

Expected: no output (success).

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: matrix unit tests (Linux/macOS/Windows) + Linux integration"
```

---

## Phase 8 — Docs + packaging polish

### Task 22: Rewrite README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Overwrite README.md with the new architecture and quick-start**

Replace the entire file contents with:

````markdown
# dictate

**Offline, privacy-first speech-to-text for your terminal.** Hold a global hotkey, speak, release — your words are transcribed locally via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and copied to your clipboard. Nothing leaves your machine.

A Python daemon with a Textual TUI for configuration, status, and history.

## Features

- **Global push-to-talk hotkey** — `ctrl+shift+d` by default.
- **100% offline** — faster-whisper runs on-device (first run downloads the model).
- **Auto-paste** — optional paste-at-cursor (X11/mac/Win: pynput; Wayland: ydotool).
- **History** — scrollable list of past transcriptions.
- **TUI for everything else** — `dictate tui` opens a terminal UI with live status, settings, and history.

## Install

```bash
pipx install dictate    # or: pip install --user dictate
```

Requires Python 3.11+ and `libportaudio2` on Linux.

## Quick start

```bash
# Run the daemon in one terminal (Ctrl+C to stop)
dictate

# In another terminal, open the config TUI
dictate tui
```

Hold `ctrl+shift+d` to record, release to transcribe. The transcription lands in your clipboard.

## Commands

| Command | What it does |
|---|---|
| `dictate` | Run the daemon (foreground). |
| `dictate tui` | Open the Textual TUI (requires a running daemon). |
| `dictate toggle` | Send SIGUSR1 — toggle recording. For Wayland compositor bindings. |
| `dictate start` / `dictate stop` | Same signal; for Sway/i3 `bindsym --release` pairs. |
| `dictate --version` | Print version. |

## Configuration

The daemon reads `~/.config/dictate/config.toml`. On first run it writes a fully-commented default. Edit by hand or use `dictate tui`. Changes take effect on `SIGHUP` (the TUI sends this automatically on save).

Structural changes (model size, device, compute type, mic) require a daemon restart — the TUI prompts you.

## Wayland setup

Wayland compositors don't expose a universal global-hotkey API, so you bind `dictate toggle` manually in your compositor's keyboard settings.

**KDE Plasma:** System Settings → Shortcuts → Add Application → Command: `dictate toggle`

**Sway / Hyprland:** add to config:
```
bindsym ctrl+shift+d exec dictate toggle
# For true push-to-talk (Sway):
# bindsym ctrl+shift+d exec dictate start
# bindsym --release ctrl+shift+d exec dictate stop
```

**GNOME:** Settings → Keyboard → Custom Shortcuts → Add: Command: `dictate toggle`

Auto-paste on Wayland requires `ydotool` + `ydotoold`. See the systemd unit example in [DEBUGGING.md](DEBUGGING.md).

## Run at login (systemd)

```ini
# ~/.config/systemd/user/dictate.service
[Unit]
Description=dictate — offline speech-to-text daemon

[Service]
Type=simple
ExecStart=%h/.local/bin/dictate
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now dictate
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design. TL;DR: one Python daemon + one Textual TUI, sharing state via files in XDG dirs + POSIX signals.

## License

[MIT](LICENSE) © 2026 Geoffrey Byers
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README for Python daemon + TUI architecture"
```

---

### Task 23: Rewrite ARCHITECTURE.md

**Files:**
- Modify: `ARCHITECTURE.md`

- [ ] **Step 1: Replace ARCHITECTURE.md contents**

The new architecture doc mirrors the approved spec, trimmed to an engineer-onboarding shape. Use this as the body:

````markdown
# dictate — Architecture

## Overview

dictate is a privacy-first speech-to-text tool. Two Python processes cooperate via files on disk and POSIX signals: the **daemon** (hotkey + audio + transcription + clipboard) and the **TUI** (Textual; status / settings / history).

## Processes

**Daemon (`dictate`)**
- Loads the faster-whisper model at startup.
- Listens for the configured global hotkey via pynput.
- Captures audio with sounddevice on press, stops on release.
- Queues the buffer for transcription (single worker).
- Writes the result to the clipboard, optionally auto-pastes, and appends to history.
- Reloads config on `SIGHUP`; toggles recording on `SIGUSR1`; clean exit on `SIGTERM`/`SIGINT`.

**TUI (`dictate tui`)**
- Textual app. Three screens: Status, Settings, History.
- Reads `config.toml`, `status.json`, `history.jsonl`.
- Polls `status.json` at 10 Hz for the live footer.
- On Save: atomic write of `config.toml`, then `SIGHUP` to the daemon.
- Refuses to launch if the daemon isn't running (no auto-spawn).

## Files (XDG dirs)

| File | Writer | Readers | Purpose |
|---|---|---|---|
| `~/.config/dictate/config.toml` | TUI, user | daemon | Settings. |
| `~/.cache/dictate/status.json` | daemon | TUI, user scripts | Runtime state. |
| `~/.local/share/dictate/history.jsonl` | daemon | TUI | Transcription history. |
| `~/.local/share/dictate/dictate.log` | daemon | user | Rotating log. |
| `~/.cache/dictate/dictate.pid` | daemon | TUI, signal CLIs | PID + start timestamp. |

## Signal contract

- `SIGHUP` — reload config. Structural changes (model/device/mic) set `needs_restart=true` in status.
- `SIGUSR1` — toggle recording (respects `hotkey.mode`).
- `SIGTERM` / `SIGINT` — drain queue (5 s deadline), remove PID, exit 0.

## Why files + signals, not WebSocket / RPC

- OS-level primitives we don't have to version or handshake.
- No protocol churn between TUI and daemon.
- Users can inspect everything with `cat` / `jq` and script custom integrations.

## Platform notes

- **Linux X11**: push-to-talk via pynput. Clipboard via pyperclip. Auto-paste via pynput.
- **Linux Wayland**: hotkey not exposed to apps. User binds `dictate toggle` in their compositor. Sway/i3 `bindsym --release` can recover push-to-talk. Auto-paste via `ydotool`.
- **macOS**: pynput (needs Accessibility permission). No portal plumbing.
- **Windows**: pynput. No special setup.

## Module map

```
dictate/
├── __main__.py     python -m dictate → daemon
├── cli.py          argparse dispatch (daemon / tui / toggle / start / stop)
├── daemon.py       Main loop, signal handlers, orchestration
├── config.py       TOML load/save, defaults, validation
├── hotkey.py       Binding parser + HOLD/TOGGLE state machine + pynput wiring
├── recorder.py     sounddevice mic capture
├── transcriber.py  faster-whisper wrapper
├── jobs.py         Single-worker transcription queue (deque + thread)
├── clipboard.py    pyperclip wrapper
├── paste.py        Platform dispatch (pynput / ydotool)
├── state.py        PID, status.json, history.jsonl (atomic writes)
├── log.py          Rotating file logger
├── paths.py        XDG path helpers
├── errors.py       Typed exceptions
└── tui/
    ├── app.py      Textual App + routing
    ├── footer.py   Live status footer
    ├── status.py   Status screen
    ├── settings.py Settings screen (form + save bar)
    └── history.py  History screen
```

## Testing

- Unit tests cover config, state, jobs queue, hotkey state machine, paste dispatch, and hardware-adapter dispatch (with `unittest.mock`).
- TUI tests use Textual's `App.run_test()` pilot.
- Integration tests start the daemon in a subprocess with hardware stubs and verify signal contracts.

CI (GitHub Actions): matrix unit tests on Linux/macOS/Windows; integration tests on Linux.
````

- [ ] **Step 2: Commit**

```bash
git add ARCHITECTURE.md
git commit -m "docs: rewrite ARCHITECTURE.md for the Python daemon + TUI design"
```

---

### Task 24: Light edits to DEBUGGING.md / CONTRIBUTING.md / SECURITY.md

**Files:**
- Modify: `DEBUGGING.md`, `CONTRIBUTING.md`, `SECURITY.md`

- [ ] **Step 1: Replace `DEBUGGING.md` with Python-stack guidance**

```markdown
# Debugging dictate

## Logs

Daemon logs to `~/.local/share/dictate/dictate.log` (rotating, 10 MB × 3 by default; tune in `[logs]`).

```bash
tail -f ~/.local/share/dictate/dictate.log
```

Set `logs.level = "debug"` for verbose output.

## Runtime state

```bash
cat ~/.cache/dictate/status.json | jq
```

## Verbose daemon (foreground)

Run the daemon from a terminal to see stderr too:

```bash
dictate 2>&1 | tee /tmp/dictate.log
```

## Wayland auto-paste (ydotool)

If auto-paste silently falls back to clipboard-only:

```bash
# Check ydotoold
systemctl --user status ydotoold.service

# Test ydotool by hand
echo "ctrl+v" | ydotool key ctrl+v
```

Reference systemd unit for `ydotoold`:

```ini
[Unit]
Description=ydotool user daemon

[Service]
Type=simple
ExecStart=/usr/bin/ydotoold --socket-path=%t/.ydotool_socket --socket-own=%U:%G
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
```

## No microphone / no device

`~/.cache/dictate/status.json.last_error` will contain the detail. Fix the device in `[audio].microphone` or leave it blank for the system default. Run `python -c "import sounddevice; print(sounddevice.query_devices())"` to list devices.

## Tests

```bash
pytest tests/unit -v
pytest tests/tui -v
pytest tests/integration -v
```
```

- [ ] **Step 2: Update `CONTRIBUTING.md` — replace any Node/Rust references with Python**

Replace file contents with:

```markdown
# Contributing

## Dev environment

```bash
python3 -m venv .venv
.venv/bin/pip install -e .[dev]
```

## Run the daemon

```bash
.venv/bin/dictate
```

## Tests

```bash
.venv/bin/pytest
```

TDD expected: add a failing test, implement, commit.

## Style

- Small, focused modules. One clear responsibility per file.
- Typed exceptions live in `dictate/errors.py`.
- Don't mock the daemon; mock the hardware (`Transcriber`, `Recorder`, `HotkeyListener`).
- Keep TUI screens free of I/O — read through `dictate.paths` helpers.

## Commits

Conventional commit prefixes: `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `ci:`. Include scope in parens where useful (`feat(tui): ...`).

## Opening a PR

- Ensure `pytest` is green locally.
- Update `README.md` / `ARCHITECTURE.md` if behavior or module layout changes.
```

- [ ] **Step 3: Update `SECURITY.md` — light edit**

Remove any references to the React/Tauri frontend or webview. Keep the privacy/threat-model language. If SECURITY.md has repo-specific reporting instructions, preserve them. Minimum change: ensure no dead references to WebView, Tauri, or the sidecar.

- [ ] **Step 4: Commit**

```bash
git add DEBUGGING.md CONTRIBUTING.md SECURITY.md
git commit -m "docs: update DEBUGGING/CONTRIBUTING/SECURITY for Python stack"
```

---

### Task 25: Packaging polish + smoke run

**Files:**
- Modify: `pyproject.toml` (final metadata pass), `LICENSE` (verify unchanged)
- New: `MANIFEST.in` if needed

- [ ] **Step 1: Add PyPI metadata to pyproject.toml**

Edit `[project]` section — add keywords, classifiers, urls:

```toml
[project]
# ... existing fields ...
keywords = ["speech-to-text", "whisper", "dictation", "tui", "cli", "privacy"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Environment :: Console :: Curses",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: MIT License",
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS :: MacOS X",
    "Operating System :: Microsoft :: Windows",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Multimedia :: Sound/Audio :: Speech",
]

[project.urls]
Homepage = "https://github.com/geoffreybyers/dictate"
Issues = "https://github.com/geoffreybyers/dictate/issues"
```

- [ ] **Step 2: Build a wheel locally to verify**

```bash
.venv/bin/pip install build
.venv/bin/python -m build --wheel
ls dist/
```

Expected: `dist/dictate-2.0.0.dev0-py3-none-any.whl` exists.

- [ ] **Step 3: Install the wheel fresh in a throwaway venv and run `--version`**

```bash
python3 -m venv /tmp/dictate-smoketest
/tmp/dictate-smoketest/bin/pip install dist/dictate-*.whl
/tmp/dictate-smoketest/bin/dictate --version
```

Expected: `dictate 2.0.0.dev0`.

Clean up:

```bash
rm -rf /tmp/dictate-smoketest dist build dictate.egg-info
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: PyPI metadata + classifiers"
```

---

### Task 26: Final manual smoke + merge preparation

**Files:** none — verification only.

- [ ] **Step 1: Full test suite**

```bash
.venv/bin/pytest -v
```

Expected: all green.

- [ ] **Step 2: Real end-to-end smoke (local, manual)**

On the dev machine:

1. Run `.venv/bin/dictate` in one terminal. Expect `listening for [ctrl+shift+d]…` (or similar) and no tracebacks.
2. In another terminal: `.venv/bin/dictate tui`. Expect the TUI opens to Status showing `IDLE`.
3. Press `s` in TUI → Settings screen renders fields.
4. Press `h` in TUI → History screen renders (may be empty; that's fine).
5. Press `ctrl+shift+d` in any focused app (hold, say a short phrase, release). The daemon terminal should log transcription; clipboard should contain the text.
6. `dictate toggle` from another terminal → recording flips; toggle again to stop.
7. Ctrl+C the daemon → clean exit, PID file removed.

Record any surprises in a GitHub issue; do not attempt in-scope fixes — they're out of this plan.

- [ ] **Step 3: Prepare the merge**

```bash
git log --oneline main..HEAD      # review the commit history
```

When the PR is approved:

```bash
git push -u origin rebuild/python-tui
gh pr create --title "dictate v2: replace GUI with TUI + Python daemon" \
             --body-file docs/superpowers/specs/2026-04-18-cli-replaces-gui-design.md
```

---

## Self-review checklist (plan author)

- [x] Every spec section has a corresponding task (architecture → Tasks 14–16; files layout → Tasks 5, 14; settings schema → Task 4; TUI → Tasks 16–19; daemon internals → Tasks 14, 10–13; testing → Tasks 3–21; packaging → Tasks 2, 25; deletions → Task 1).
- [x] No `TBD` / `TODO` / "implement later" markers in any step.
- [x] Type and method-name consistency across tasks: `HotkeyState`, `HotkeyListener`, `Mode`, `StateWriter`, `StatusSnapshot`, `HistoryEntry`, `TranscriptionResult`, `TranscriptionQueue`, `Daemon`.
- [x] `jobs.py` deviation from spec (to avoid stdlib `queue` shadowing) documented at the top.
- [x] Test code included where a step writes tests; commit commands included at every boundary.
