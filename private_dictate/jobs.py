"""Single-worker transcription queue with overflow-drops-oldest semantics."""
from __future__ import annotations

import logging
import threading
from collections import deque
from typing import Any, Callable

from private_dictate.errors import QueueOverflowError

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
        self._thread = threading.Thread(target=self._run, daemon=True, name="private-dictate-queue")
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
