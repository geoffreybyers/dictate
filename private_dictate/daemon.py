"""Daemon: model load, hotkey listener, queue, signal handlers. Foreground process."""
from __future__ import annotations

import datetime as dt
import logging
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from private_dictate import clipboard, log, paste, paths
from private_dictate.config import Config, load as load_config
from private_dictate.errors import PrivateDictateError
from private_dictate.hotkey import HotkeyListener, Mode
from private_dictate.jobs import TranscriptionQueue
from private_dictate.recorder import Recorder
from private_dictate.state import HistoryEntry, StateWriter, StatusSnapshot
from private_dictate.transcriber import Transcriber, TranscriptionResult


class Daemon:
    def __init__(self, cfg: Optional[Config] = None):
        self._cfg = cfg if cfg is not None else load_config(paths.config_path())
        self._state = StateWriter(
            cache_dir=paths.cache_dir(),
            data_dir=paths.data_dir(),
            history_limit=self._cfg.history.limit,
        )
        self._transcriber: Optional[Transcriber] = None
        self._recorder: Optional[Recorder] = None
        self._hotkey: Optional[HotkeyListener] = None
        self._queue: Optional[TranscriptionQueue] = None
        self._stop_event = threading.Event()
        self._needs_restart = False
        self._last_error: Optional[str] = None

    # --- lifecycle ----------------------------------------------------------

    def setup(self) -> None:
        log.configure(paths.log_path(),
                      level=self._cfg.logs.level,
                      max_size_mb=self._cfg.logs.max_size_mb)
        logging.getLogger("private_dictate").info("daemon starting")
        self._state.write_pid()
        self._install_signal_handlers()

        self._transcriber = Transcriber(
            size=self._cfg.model.size,
            device=self._cfg.model.device,
            compute_type=self._cfg.model.compute_type,
            cache_dir=Path(self._cfg.model.cache_dir) if self._cfg.model.cache_dir else None,
        )
        self._recorder = Recorder(mic=self._cfg.audio.microphone or None)
        self._queue = TranscriptionQueue(self._process_audio, max_depth=10)
        self._hotkey = HotkeyListener(
            binding=self._cfg.hotkey.binding,
            mode=Mode(self._cfg.hotkey.mode),
            on_start=self._start_recording,
            on_stop=self._stop_recording,
        )
        self._write_status("idle")

    def run(self) -> int:
        self.setup()
        self._queue.start()
        self._hotkey.start()
        try:
            while not self._stop_event.is_set():
                self._write_status(self._derive_state())
                self._stop_event.wait(0.2)
            return 0
        finally:
            self._shutdown()

    # --- signal handlers ----------------------------------------------------

    def _install_signal_handlers(self) -> None:
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        signal.signal(signal.SIGINT, self._handle_sigterm)
        signal.signal(signal.SIGHUP, self._handle_sighup)
        signal.signal(signal.SIGUSR1, self._handle_sigusr1)

    def _handle_sigterm(self, signum, frame) -> None:
        logging.getLogger("private_dictate").info("SIGTERM/SIGINT received — shutting down")
        self._stop_event.set()

    def _handle_sighup(self, signum, frame) -> None:
        logging.getLogger("private_dictate").info("SIGHUP — reloading config")
        try:
            new_cfg = load_config(paths.config_path())
        except PrivateDictateError as e:
            self._last_error = f"config reload failed: {e}"
            return
        needs_restart = self._structural_change(self._cfg, new_cfg)
        self._cfg = new_cfg
        if needs_restart:
            self._needs_restart = True
            logging.getLogger("private_dictate").warning(
                "structural config change — restart required"
            )

    def _handle_sigusr1(self, signum, frame) -> None:
        if self._hotkey:
            self._hotkey.external_toggle()

    @staticmethod
    def _structural_change(old: Config, new: Config) -> bool:
        return (
            old.model.size != new.model.size
            or old.model.device != new.model.device
            or old.model.compute_type != new.model.compute_type
            or old.model.cache_dir != new.model.cache_dir
            or old.audio.microphone != new.audio.microphone
        )

    # --- recording + transcription -----------------------------------------

    def _start_recording(self) -> None:
        try:
            self._recorder.start()
        except PrivateDictateError as e:
            self._last_error = str(e)

    def _stop_recording(self) -> None:
        audio = self._recorder.stop()
        if audio.size == 0:
            return
        try:
            self._queue.enqueue(audio)
        except PrivateDictateError as e:
            self._last_error = str(e)

    def _process_audio(self, audio) -> None:
        try:
            result: TranscriptionResult = self._transcriber.transcribe(audio)
        except Exception as e:
            self._last_error = f"transcription failed: {e}"
            logging.getLogger("private_dictate").exception("transcription failed")
            return
        if not result.text:
            return
        clipboard.copy(result.text)
        if self._cfg.transcription.autopaste:
            paste.paste(self._cfg.transcription.paste_shortcut)
        if self._cfg.history.save:
            self._state.append_history(HistoryEntry(
                ts=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                text=result.text,
                duration_ms=result.duration_ms,
                language=result.language,
                confidence=result.confidence,
            ))

    # --- status -------------------------------------------------------------

    def _derive_state(self) -> str:
        if self._last_error:
            return "error"
        if self._hotkey and self._hotkey._state.recording:
            return "recording"
        if self._queue and self._queue.depth() > 0:
            return "transcribing"
        return "idle"

    def _write_status(self, state: str) -> None:
        import os as _os
        snap = StatusSnapshot(
            state=state,
            recording=bool(self._hotkey and self._hotkey._state.recording),
            queue_depth=self._queue.depth() if self._queue else 0,
            last_error=self._last_error,
            pid=_os.getpid(),
            uptime_s=self._state.uptime_s(),
            model_loaded=self._transcriber is not None,
            needs_restart=self._needs_restart,
            device=self._transcriber.device if self._transcriber else None,
            compute_type=self._transcriber.compute_type if self._transcriber else None,
            model_notice=self._transcriber.last_error if self._transcriber else None,
        )
        self._state.write_status(snap)

    # --- shutdown -----------------------------------------------------------

    def _shutdown(self) -> None:
        logging.getLogger("private_dictate").info("daemon shutting down")
        if self._hotkey:
            self._hotkey.stop()
        if self._queue:
            self._queue.stop(timeout=5.0)
        self._state.clear_pid()


def main() -> int:
    return Daemon().run()


if __name__ == "__main__":
    sys.exit(main())
