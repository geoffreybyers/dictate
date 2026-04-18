"""
Transcription job queue: deque + single worker thread.
Max depth 10; drop oldest on overflow with warning.
"""
import threading
import time
from collections import deque
from typing import Any, Callable

MAX_QUEUE_DEPTH = 10


def process_queue(
    queue: deque,
    lock: threading.Lock,
    worker: Callable[[Any], dict | None],
    on_transcribing: Callable[[int], None],
    on_complete: Callable[[dict], None],
    on_empty: Callable[[], None],
    on_overflow: Callable[[], None],
    stop_event: threading.Event,
) -> None:
    """
    Worker loop: pull one job (audio buffer) at a time, run worker(audio), emit result.
    on_transcribing(depth) with current queue depth; on_complete(payload) or on_empty().
    payload is a dict with at least "text"; may include duration_ms, confidence, detected_language.
    Stops when stop_event is set.
    """
    while not stop_event.is_set():
        with lock:
            if not queue:
                pass
            else:
                depth = len(queue)
                audio = queue.popleft()
                # Release lock before doing heavy work
                lock.release()
                try:
                    on_transcribing(depth)
                    result = worker(audio)
                    if result:
                        on_complete(result)
                    else:
                        on_empty()
                finally:
                    lock.acquire()
                continue
        time.sleep(0.1)


def enqueue(
    queue: deque,
    lock: threading.Lock,
    audio: Any,
    on_overflow: Callable[[], None],
) -> bool:
    """Append audio buffer. If len >= MAX_QUEUE_DEPTH, drop oldest and call on_overflow. Returns True if enqueued."""
    with lock:
        if len(queue) >= MAX_QUEUE_DEPTH:
            queue.popleft()
            on_overflow()
        queue.append(audio)
    return True
