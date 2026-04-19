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
