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
