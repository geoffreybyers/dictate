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
