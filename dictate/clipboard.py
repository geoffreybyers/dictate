"""Clipboard writes via pyperclip. Failures log and return."""
from __future__ import annotations

import logging

import pyperclip

log = logging.getLogger(__name__)


def copy(text: str) -> None:
    try:
        pyperclip.copy(text)
    except Exception as e:
        log.warning("clipboard write failed: %s", e)
