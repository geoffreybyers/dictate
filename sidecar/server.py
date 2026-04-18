"""
FastAPI WebSocket server: single /ws endpoint, message routing, model/recorder/queue.
"""
import asyncio
import json
import os
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from settings import load as load_settings, save as save_settings, validate as validate_settings
from task_queue import process_queue, enqueue, MAX_QUEUE_DEPTH
from recorder import Recorder, SAMPLE_RATE
from transcriber import Transcriber

# Set by main.py before uvicorn runs
CONFIG_PATH: Optional[str] = None

# CUDA detection: faster-whisper uses CTranslate2; GPU support depends on the ctranslate2 build.
def _cuda_available() -> bool:
    try:
        import ctranslate2
        # get_supported_devices() exists only in some ctranslate2 versions; use get_cuda_device_count.
        if hasattr(ctranslate2, "get_cuda_device_count"):
            count = ctranslate2.get_cuda_device_count()
            print(f"[dictate] CTranslate2 CUDA device count: {count}", flush=True)
            return count > 0
        if hasattr(ctranslate2, "get_supported_devices"):
            devices = ctranslate2.get_supported_devices()
            print(f"[dictate] CTranslate2 supported devices: {devices}", flush=True)
            return "cuda" in devices
        # Fallback: try get_supported_compute_types("cuda") — if it returns a non-empty set, CUDA is available.
        if hasattr(ctranslate2, "get_supported_compute_types"):
            types = ctranslate2.get_supported_compute_types("cuda")
            available = bool(types)
            print(f"[dictate] CTranslate2 CUDA compute types: {types if available else 'none'}", flush=True)
            return available
        print("[dictate] CTranslate2: no device query API found", flush=True)
        return False
    except Exception as e:
        print(f"[dictate] CTranslate2 device check failed: {e}", flush=True)
        return False


def _get_cuda_version() -> Optional[str]:
    """Return CUDA version string from nvidia-smi (e.g. '12.2' or '13.0') or None if unavailable."""
    # Prefer structured query (supported in many nvidia-smi versions)
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=cuda_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0 and out.stdout:
            version = out.stdout.splitlines()[0].strip()
            if version:
                return version
    except (FileNotFoundError, subprocess.TimeoutExpired, IndexError, Exception):
        pass
    # Fallback: parse default nvidia-smi output for "CUDA Version: X.Y"
    try:
        out = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode != 0 or not out.stdout:
            return None
        for line in out.stdout.splitlines():
            if "CUDA Version" in line:
                # e.g. "|    CUDA Version: 13.0     |" or "CUDA Version: 12.2"
                parts = line.split("CUDA Version:")
                if len(parts) >= 2:
                    version = parts[1].strip().strip("|").strip()
                    if version:
                        return version
                break
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return None


def get_session_type() -> str:
    """Returns 'x11', 'wayland', or 'unknown'."""
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session in ("x11", "wayland"):
        return session
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return "unknown"


app = FastAPI()

# Per-connection state (single client expected)
_state: dict[str, Any] = {}


async def _emit(ws: WebSocket, msg: dict[str, Any]) -> None:
    try:
        await ws.send_text(json.dumps(msg))
    except Exception:
        pass


async def _run_connection(websocket: WebSocket) -> None:
    global _state
    config_path = CONFIG_PATH or ""
    if not config_path:
        await _emit(websocket, {"type": "error", "code": "NO_CONFIG", "message": "No config path"})
        return

    current_settings = load_settings(config_path)
    device = current_settings.get("device", "cpu")
    compute_type = current_settings.get("compute_type") or (
        "int8" if device == "cpu" else "float16"
    )
    cuda_available = _cuda_available()
    if device == "cuda" and not cuda_available:
        print("[dictate] CUDA requested but not available; using CPU for transcription.", flush=True)
        device = "cpu"
        compute_type = "int8"
        current_settings["device"] = device
        current_settings["compute_type"] = compute_type

    session_type = get_session_type()
    cuda_version: Optional[str] = _get_cuda_version() if cuda_available else None
    recorder: Optional[Recorder] = None
    transcriber: Optional[Transcriber] = None
    queue: deque = deque()
    queue_lock = threading.Lock()
    queue_stop = threading.Event()
    queue_thread: Optional[threading.Thread] = None
    loop = asyncio.get_running_loop()

    def _emit_sync(msg: dict[str, Any]) -> None:
        """Schedule _emit on the main loop from the queue worker thread."""
        asyncio.run_coroutine_threadsafe(_emit(websocket, msg), loop)

    def on_overflow() -> None:
        _emit_sync({"type": "error", "code": "QUEUE_OVERFLOW", "message": "Queue full, dropped oldest"})

    def on_transcribing(depth: int) -> None:
        _emit_sync({"type": "transcribing", "queue_depth": depth})

    def on_complete(payload: dict) -> None:
        msg: dict[str, Any] = {
            "type": "transcription_complete",
            "text": payload["text"],
            "duration_ms": payload.get("duration_ms", 0),
        }
        if payload.get("confidence") is not None:
            msg["confidence"] = payload["confidence"]
        if payload.get("detected_language") is not None:
            msg["detected_language"] = payload["detected_language"]
        if payload.get("transcription_ms") is not None:
            msg["transcription_ms"] = payload["transcription_ms"]
        _emit_sync(msg)

    def on_empty() -> None:
        _emit_sync({"type": "transcription_empty"})

    def worker(audio: Any) -> Optional[dict]:
        if transcriber is None:
            return None
        t0 = time.perf_counter()
        result = transcriber.transcribe(audio)
        t1 = time.perf_counter()
        if result is None:
            return None
        transcription_ms = int((t1 - t0) * 1000)
        out: dict[str, Any] = {
            "text": result.text,
            "duration_ms": result.duration_ms,
            "transcription_ms": transcription_ms,
            "confidence": result.confidence,
            "detected_language": result.detected_language,
        }
        return out

    try:
        # Model loading
        await _emit(websocket, {"type": "model_loading"})
        t0 = time.perf_counter()
        try:
            transcriber = Transcriber(
                model_size=current_settings["model_size"],
                device=device,
                compute_type=compute_type,
                language=current_settings.get("language") or "en",
                vad_filter=current_settings.get("vad_filter", True),
            )
        except Exception as e:
            await _emit(websocket, {"type": "error", "code": "MODEL_LOAD_FAILED", "message": str(e)})
            return
        load_time_ms = int((time.perf_counter() - t0) * 1000)
        await _emit(websocket, {"type": "model_ready", "load_time_ms": load_time_ms})
        ready_payload: dict[str, Any] = {
            "type": "ready",
            "device": device,
            "model": current_settings["model_size"],
            "cuda_available": cuda_available,
            "session_type": session_type,
            "hotkey": current_settings.get("hotkey", "Space"),
            "auto_paste": current_settings.get("auto_paste", False),
        }
        if cuda_version is not None:
            ready_payload["cuda_version"] = cuda_version
        await _emit(websocket, ready_payload)

        # Start queue worker thread
        queue_stop.clear()
        queue_thread = threading.Thread(
            target=process_queue,
            args=(queue, queue_lock, worker, on_transcribing, on_complete, on_empty, on_overflow, queue_stop),
            daemon=True,
        )
        queue_thread.start()

        recorder = Recorder(sample_rate=SAMPLE_RATE)
        _state["recorder"] = recorder
        _state["queue"] = queue
        _state["queue_lock"] = queue_lock
        _state["on_overflow"] = on_overflow
        _state["settings"] = current_settings
        _state["config_path"] = config_path

        # Command loop
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            cmd = data.get("type")

            if cmd == "start_recording":
                try:
                    recorder.start_recording()
                    await _emit(websocket, {"type": "recording_started"})
                except Exception as e:
                    await _emit(websocket, {"type": "error", "code": "NO_MICROPHONE", "message": str(e)})

            elif cmd == "stop_recording":
                buffer = recorder.stop_recording()
                await _emit(websocket, {"type": "recording_stopped"})
                if buffer is not None:
                    enqueue(queue, queue_lock, buffer, on_overflow)

            elif cmd == "toggle_recording":
                if recorder._recording.is_set():
                    buffer = recorder.stop_recording()
                    await _emit(websocket, {"type": "recording_stopped"})
                    if buffer is not None:
                        enqueue(queue, queue_lock, buffer, on_overflow)
                else:
                    try:
                        recorder.start_recording()
                        await _emit(websocket, {"type": "recording_started"})
                    except Exception as e:
                        await _emit(websocket, {"type": "error", "code": "NO_MICROPHONE", "message": str(e)})

            elif cmd == "update_settings":
                new_settings = data.get("settings", {})
                if isinstance(new_settings, dict):
                    current_settings.update(validate_settings({**current_settings, **new_settings}))
                    save_settings(config_path, current_settings)
                    await _emit(websocket, {"type": "settings_saved"})

            elif cmd == "get_status":
                status_payload: dict[str, Any] = {
                    "type": "ready",
                    "device": device,
                    "model": current_settings["model_size"],
                    "cuda_available": cuda_available,
                    "session_type": session_type,
                    "hotkey": current_settings.get("hotkey", "Space"),
                    "auto_paste": current_settings.get("auto_paste", False),
                }
                if cuda_version is not None:
                    status_payload["cuda_version"] = cuda_version
                await _emit(websocket, status_payload)

            elif cmd == "shutdown":
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await _emit(websocket, {"type": "error", "code": "TRANSCRIPTION_FAILED", "message": str(e)})
    finally:
        queue_stop.set()
        _state.clear()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await _run_connection(websocket)
