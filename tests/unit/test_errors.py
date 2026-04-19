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
