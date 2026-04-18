# Model options: "tiny", "base", "small", "medium", "large-v3"
MODEL_SIZE = "small"

# Device options: "cpu", "cuda"
# "cuda" requires CUDA toolkit and compatible nvidia-cublas-cu12 / nvidia-cudnn-cu12
DEVICE = "cpu"

# Compute type — must match device:
#   cpu  → "int8"
#   cuda → "float16" or "int8_float16"
COMPUTE_TYPE = "int8"

# Language: "en" for English, None for auto-detect (slower)
LANGUAGE = "en"

# Hotkey: any key string pynput recognizes, e.g. "space", "shift", "f9"
HOTKEY = "space"

# VAD filter: strips silence from audio before transcription. Recommended True.
VAD_FILTER = True

# Sample rate: do not change. Whisper requires 16000 Hz.
SAMPLE_RATE = 16000

# Warm-up: run a silent transcription at startup to pre-cache model internals.
WARMUP = True
