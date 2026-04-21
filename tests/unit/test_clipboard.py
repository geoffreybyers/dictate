from unittest.mock import patch
from private_dictate.clipboard import copy


def test_copy_calls_pyperclip():
    with patch("private_dictate.clipboard.pyperclip") as pc:
        copy("hello")
        pc.copy.assert_called_once_with("hello")


def test_copy_swallows_pyperclip_exception(caplog):
    import pyperclip
    with patch("private_dictate.clipboard.pyperclip") as pc:
        pc.copy.side_effect = pyperclip.PyperclipException("no backend")
        copy("hello")  # must not raise
    assert any("clipboard" in rec.message.lower() for rec in caplog.records)
