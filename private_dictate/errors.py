"""Typed exceptions used across PrivateDictate."""


class PrivateDictateError(Exception):
    """Base class for all PrivateDictate errors."""


class ConfigError(PrivateDictateError):
    """Invalid or unparseable configuration."""


class AudioError(PrivateDictateError):
    """Microphone / recording failed."""


class TranscriptionError(PrivateDictateError):
    """Transcription pipeline failed."""


class QueueOverflowError(PrivateDictateError):
    """Transcription queue exceeded max depth."""


class PasteUnavailableError(PrivateDictateError):
    """Auto-paste backend unavailable on this platform."""
