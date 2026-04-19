from unittest.mock import patch, MagicMock
import numpy as np
import pytest
from dictate.recorder import Recorder
from dictate.errors import AudioError


def test_start_then_stop_returns_concatenated_buffer():
    with patch("dictate.recorder.sd") as sd:
        stream = MagicMock()
        sd.InputStream.return_value = stream
        rec = Recorder()
        rec.start()
        # simulate 3 callbacks, each 1024 float32 frames
        cb = sd.InputStream.call_args.kwargs["callback"]
        cb(np.ones((1024, 1), dtype=np.float32), 1024, None, None)
        cb(np.ones((1024, 1), dtype=np.float32) * 2, 1024, None, None)
        cb(np.ones((1024, 1), dtype=np.float32) * 3, 1024, None, None)
        audio = rec.stop()
        assert audio.shape == (3072,)
        assert np.allclose(audio[:1024], 1.0)
        assert np.allclose(audio[2048:], 3.0)


def test_stop_without_start_returns_empty():
    with patch("dictate.recorder.sd"):
        rec = Recorder()
        audio = rec.stop()
        assert audio.size == 0


def test_start_failure_raises_audio_error():
    with patch("dictate.recorder.sd") as sd:
        sd.InputStream.side_effect = Exception("no device")
        rec = Recorder()
        with pytest.raises(AudioError):
            rec.start()
