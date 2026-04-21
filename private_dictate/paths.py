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
