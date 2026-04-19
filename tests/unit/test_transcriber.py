from unittest.mock import patch, MagicMock
import numpy as np
from dictate.transcriber import Transcriber, TranscriptionResult


def test_transcribe_returns_result_struct():
    segments = [MagicMock(text=" hello ", avg_logprob=-0.1, no_speech_prob=0.1),
                MagicMock(text=" world", avg_logprob=-0.2, no_speech_prob=0.1)]
    info = MagicMock(language="en", duration=1.5)
    with patch("dictate.transcriber.WhisperModel") as WM:
        wm = MagicMock()
        wm.transcribe.return_value = (iter(segments), info)
        WM.return_value = wm
        t = Transcriber(size="small", device="cpu", compute_type="int8")
        result = t.transcribe(np.zeros(16000, dtype=np.float32))
    assert isinstance(result, TranscriptionResult)
    assert result.text == "hello world"
    assert result.language == "en"
    assert 0.0 <= result.confidence <= 1.0


def test_empty_audio_returns_empty_text():
    with patch("dictate.transcriber.WhisperModel"):
        t = Transcriber(size="small", device="cpu", compute_type="int8")
        result = t.transcribe(np.zeros(0, dtype=np.float32))
    assert result.text == ""
