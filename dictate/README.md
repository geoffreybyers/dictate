# Dictate CLI v1

Local, privacy-first speech-to-text: push-to-talk, on-device transcription (faster-whisper), clipboard copy. No audio or text leaves your machine.

## Setup

1. **Python 3.10+** and a virtual environment (recommended):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   ```

2. **Install dependencies** (from the project root, or from the directory containing `dictate/`):

   ```bash
   pip install -r dictate/requirements.txt
   ```

3. **Optional — CUDA:** For GPU acceleration you need a CUDA-capable system and:

   ```bash
   pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
   ```

   Then set `DEVICE = "cuda"` and `COMPUTE_TYPE = "float16"` (or `"int8_float16"`) in `dictate/config.py`.

4. **Linux clipboard:** pyperclip needs a backend:

   ```bash
   sudo apt install xclip
   ```

## Usage

From the project root (or the directory that contains the `dictate` folder):

```bash
python dictate/main.py
```

Or from inside the `dictate` folder:

```bash
cd dictate
python main.py
```

- **Hold** the configured hotkey (default: Space) to record.
- **Release** to stop and transcribe; the result is printed and copied to the clipboard.
- **Ctrl+C** to quit.

Settings (model size, device, language, hotkey, etc.) are in `dictate/config.py`.
