from unittest.mock import patch, MagicMock
import numpy as np
import pytest
from private_dictate.transcriber import Transcriber, TranscriptionResult


def test_transcribe_returns_result_struct():
    segments = [MagicMock(text=" hello ", avg_logprob=-0.1, no_speech_prob=0.1),
                MagicMock(text=" world", avg_logprob=-0.2, no_speech_prob=0.1)]
    info = MagicMock(language="en", duration=1.5)
    with patch("private_dictate.transcriber.WhisperModel") as WM:
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
    with patch("private_dictate.transcriber.WhisperModel"):
        t = Transcriber(size="small", device="cpu", compute_type="int8")
        result = t.transcribe(np.zeros(0, dtype=np.float32))
    assert result.text == ""


def test_auto_detect_picks_cuda_when_device_count_positive():
    with patch("private_dictate.transcriber.WhisperModel") as WM, \
         patch("private_dictate.transcriber._cuda_available", return_value=True):
        t = Transcriber(size="small", device="auto", compute_type="auto")
    assert t.device == "cuda"
    assert t.compute_type == "float16"
    assert t.last_error is None
    kwargs = WM.call_args.kwargs
    assert kwargs["device"] == "cuda"
    assert kwargs["compute_type"] == "float16"


def test_auto_detect_falls_back_to_cpu_when_no_cuda():
    with patch("private_dictate.transcriber.WhisperModel") as WM, \
         patch("private_dictate.transcriber._cuda_available", return_value=False):
        t = Transcriber(size="small", device="auto", compute_type="auto")
    assert t.device == "cpu"
    assert t.compute_type == "int8"
    assert t.last_error is None
    assert WM.call_args.kwargs["device"] == "cpu"


def test_cuda_init_failure_falls_back_to_cpu_with_last_error():
    # First call (cuda) raises, second call (cpu) succeeds.
    calls = []

    def fake_wm(size, device, compute_type, download_root):
        calls.append(device)
        if device == "cuda":
            raise RuntimeError("CUDA driver missing")
        return MagicMock()

    with patch("private_dictate.transcriber.WhisperModel", side_effect=fake_wm):
        t = Transcriber(size="small", device="cuda", compute_type="auto")
    assert calls == ["cuda", "cpu"]
    assert t.device == "cpu"
    assert t.compute_type == "int8"
    assert t.last_error is not None
    assert "CUDA" in t.last_error


def test_cpu_init_failure_raises():
    with patch("private_dictate.transcriber.WhisperModel", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            Transcriber(size="small", device="cpu", compute_type="int8")
