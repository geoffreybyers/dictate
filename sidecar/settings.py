"""
Load/save settings from JSON config file.
Defaults and validation; compute_type derived from device.
"""
import json
from pathlib import Path
from typing import Any

DEFAULTS = {
    "model_size": "small",
    "device": "cpu",
    "language": "en",
    "vad_filter": True,
    "hotkey": "Space",
    "auto_paste": False,
    "paste_shortcut": "ctrl+v",
    "first_run": True,
}

VALID_MODELS = ("tiny", "base", "small", "medium", "large-v3")
VALID_DEVICES = ("cpu", "cuda")
SAMPLE_RATE = 16000


def compute_type_from_device(device: str) -> str:
    """Derive compute_type from device. cpu -> int8, cuda -> float16."""
    if device == "cpu":
        return "int8"
    if device == "cuda":
        return "float16"
    if device == "mps":
        return "float32"
    return "int8"


def load(config_path: str | Path) -> dict[str, Any]:
    """Load settings from JSON file. Create with defaults if missing."""
    path = Path(config_path)
    if path.exists():
        try:
            data = json.loads(path.read_text())
            return _validate(data)
        except (json.JSONDecodeError, OSError):
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    validated = _validate(dict(DEFAULTS))
    save(path, validated)
    return validated


def save(config_path: str | Path, settings: dict[str, Any]) -> None:
    """Write settings to JSON file. Does not store compute_type."""
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = {k: v for k, v in settings.items() if k != "compute_type"}
    path.write_text(json.dumps(out, indent=2))


def validate(data: dict[str, Any]) -> dict[str, Any]:
    """Coerce and validate; apply defaults for missing keys. Public API for merging settings."""
    return _validate(data)


def _validate(data: dict[str, Any]) -> dict[str, Any]:
    """Internal: coerce and validate."""
    model_size = str(data.get("model_size", DEFAULTS["model_size"])).lower()
    if model_size not in VALID_MODELS:
        model_size = DEFAULTS["model_size"]

    device = str(data.get("device", DEFAULTS["device"])).lower()
    if device not in VALID_DEVICES:
        device = DEFAULTS["device"]

    language = data.get("language", DEFAULTS["language"])
    if language is not None:
        language = str(language).strip() or None

    vad_filter = data.get("vad_filter", DEFAULTS["vad_filter"])
    if not isinstance(vad_filter, bool):
        vad_filter = bool(vad_filter)

    hotkey = str(data.get("hotkey", DEFAULTS["hotkey"])).strip() or DEFAULTS["hotkey"]
    auto_paste = data.get("auto_paste", DEFAULTS["auto_paste"])
    if not isinstance(auto_paste, bool):
        auto_paste = bool(auto_paste)
    paste_shortcut = str(data.get("paste_shortcut", DEFAULTS["paste_shortcut"]))
    if paste_shortcut not in ("ctrl+v", "ctrl+shift+v"):
        paste_shortcut = DEFAULTS["paste_shortcut"]
    first_run = data.get("first_run", DEFAULTS["first_run"])
    if not isinstance(first_run, bool):
        first_run = bool(first_run)

    computed = compute_type_from_device(device)
    return {
        "model_size": model_size,
        "device": device,
        "compute_type": computed,
        "language": language,
        "vad_filter": vad_filter,
        "hotkey": hotkey,
        "auto_paste": auto_paste,
        "paste_shortcut": paste_shortcut,
        "first_run": first_run,
    }
