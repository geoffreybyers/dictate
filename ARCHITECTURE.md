# PrivateDictate — Architecture

## Overview

PrivateDictate is a privacy-first speech-to-text tool. Two Python processes cooperate via files on disk and POSIX signals: the **daemon** (hotkey + audio + transcription + clipboard) and the **TUI** (Textual; status / settings / history).

## Processes

**Daemon (`private-dictate`)**
- Loads the faster-whisper model at startup.
- Listens for the configured global hotkey via pynput.
- Captures audio with sounddevice on press, stops on release.
- Queues the buffer for transcription (single worker).
- Writes the result to the clipboard, optionally auto-pastes, and appends to history.
- Reloads config on `SIGHUP`; toggles recording on `SIGUSR1`; clean exit on `SIGTERM`/`SIGINT`.

**TUI (`private-dictate tui`)**
- Textual app. Three screens: Status, Settings, History.
- Reads `config.toml`, `status.json`, `history.jsonl`.
- Polls `status.json` at 10 Hz for the live footer.
- On Save: atomic write of `config.toml`, then `SIGHUP` to the daemon.
- Refuses to launch if the daemon isn't running (no auto-spawn).

## Files (XDG dirs)

| File | Writer | Readers | Purpose |
|---|---|---|---|
| `~/.config/private-dictate/config.toml` | TUI, user | daemon | Settings. |
| `~/.cache/private-dictate/status.json` | daemon | TUI, user scripts | Runtime state. |
| `~/.local/share/private-dictate/history.jsonl` | daemon | TUI | Transcription history. |
| `~/.local/share/private-dictate/private-dictate.log` | daemon | user | Rotating log. |
| `~/.cache/private-dictate/private-dictate.pid` | daemon | TUI, signal CLIs | PID + start timestamp. |

## Signal contract

- `SIGHUP` — reload config. Structural changes (model/device/mic) set `needs_restart=true` in status.
- `SIGUSR1` — toggle recording (respects `hotkey.mode`).
- `SIGTERM` / `SIGINT` — drain queue (5 s deadline), remove PID, exit 0.

## Why files + signals, not WebSocket / RPC

- OS-level primitives we don't have to version or handshake.
- No protocol churn between TUI and daemon.
- Users can inspect everything with `cat` / `jq` and script custom integrations.

## Platform notes

- **Linux X11**: push-to-talk via pynput. Clipboard via pyperclip. Auto-paste via pynput.
- **Linux Wayland**: hotkey not exposed to apps. User binds `private-dictate toggle` in their compositor. Sway/i3 `bindsym --release` can recover push-to-talk. Auto-paste via `ydotool`.
- **macOS**: pynput (needs Accessibility permission). No portal plumbing.
- **Windows**: pynput. No special setup.

## Module map

```
private_dictate/
├── __main__.py     python -m private_dictate → daemon
├── cli.py          argparse dispatch (daemon / tui / toggle / start / stop)
├── daemon.py       Main loop, signal handlers, orchestration
├── config.py       TOML load/save, defaults, validation
├── hotkey.py       Binding parser + HOLD/TOGGLE state machine + pynput wiring
├── recorder.py     sounddevice mic capture
├── transcriber.py  faster-whisper wrapper
├── jobs.py         Single-worker transcription queue (deque + thread)
├── clipboard.py    pyperclip wrapper
├── paste.py        Platform dispatch (pynput / ydotool)
├── state.py        PID, status.json, history.jsonl (atomic writes)
├── log.py          Rotating file logger
├── paths.py        XDG path helpers
├── errors.py       Typed exceptions
└── tui/
    ├── app.py      Textual App + routing
    ├── footer.py   Live status footer
    ├── status.py   Status screen
    ├── settings.py Settings screen (form + save bar)
    └── history.py  History screen
```

## Testing

- Unit tests cover config, state, jobs queue, hotkey state machine, paste dispatch, and hardware-adapter dispatch (with `unittest.mock`).
- TUI tests use Textual's `App.run_test()` pilot.
- Integration tests start the daemon in a subprocess with hardware stubs and verify signal contracts.

CI (GitHub Actions): matrix unit tests on Linux/macOS/Windows; integration tests on Linux.
