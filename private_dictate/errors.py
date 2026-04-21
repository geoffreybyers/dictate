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
