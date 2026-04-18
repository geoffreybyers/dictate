# dictate — Architecture

## Overview

dictate is a desktop application for local, privacy-first speech-to-text. Audio is captured, transcribed on-device via [faster-whisper](https://github.com/SYSTRAN/faster-whisper), and copied to the clipboard (optionally auto-pasted). No data leaves the machine.

The app is built as two cooperating processes:

- **Tauri shell** (Rust + React webview) — window, tray, global hotkey, clipboard, IPC client.
- **Python sidecar** (FastAPI / uvicorn WebSocket server) — microphone capture, model loading, transcription queue, settings persistence.

## Technology stack

| Layer | Technology |
|---|---|
| App shell | Tauri v2 (Rust) |
| Frontend | React 19 + TypeScript + Vite |
| Styling | Tailwind CSS v3 |
| UI primitives | shadcn/ui + Radix |
| Sidecar | Python 3.11+, FastAPI, uvicorn |
| Transcription | faster-whisper (CTranslate2) |
| Audio capture | sounddevice / PortAudio |
| IPC | Local WebSocket on `127.0.0.1:39821` |

## Process architecture

```
┌──────────────────────────────────────────────────────┐
│  Tauri App (Rust)                                    │
│                                                      │
│  ┌──────────────┐       ┌────────────────────────┐   │
│  │  WebView      │       │  Rust backend          │   │
│  │  (React UI)   │◄─────►│  - Tray icon           │   │
│  │               │       │  - Window management   │   │
│  │               │       │  - Global hotkey       │   │
│  │               │       │  - Sidecar lifecycle   │   │
│  │               │       │  - Clipboard + paste   │   │
│  └──────────────┘       └──────────┬─────────────┘   │
└───────────────────────────────────-│──────────────────┘
                                     │ WebSocket
                                     │ 127.0.0.1:39821
                            ┌────────▼─────────┐
                            │  Python sidecar   │
                            │  - FastAPI / WS   │
                            │  - recorder.py    │
                            │  - transcriber.py │
                            │  - task_queue.py  │
                            └──────────────────-┘
```

### Why WebSocket over stdin/stdout

- Bidirectional messaging — the sidecar pushes status updates unprompted.
- Clean JSON framing, no newline parsing.
- The sidecar can be launched and tested independently of the Tauri shell.
- Natural path to streaming / partial results in future versions.

The port (`39821`) is fixed and the sidecar binds to `127.0.0.1` only — never exposed to the network.

## Sidecar — Python

### Responsibilities

- Load and hold the faster-whisper model in memory.
- Manage the microphone input stream.
- Transcribe audio buffers sequentially from a queue.
- Persist settings to a JSON file in the OS config directory.
- Report status, session type, and CUDA availability to the Tauri shell.

### Source layout

```
sidecar/
├── main.py         # Entry point — starts uvicorn and the WebSocket server
├── server.py       # WebSocket routing and sidecar ↔ Tauri message handling
├── recorder.py     # Microphone capture
├── transcriber.py  # faster-whisper wrapper
├── task_queue.py   # Single-worker transcription job queue
├── settings.py     # Load/save settings.json, defaults, validation
└── requirements.txt
```

### Settings file

Stored in the OS-appropriate config directory; the Tauri shell resolves the path via `app_config_dir()` and passes it to the sidecar at startup.

- Linux: `~/.config/dictate/settings.json`
- macOS: `~/Library/Application Support/dictate/settings.json`
- Windows: `%APPDATA%\dictate\settings.json`

The canonical schema lives in the TypeScript `Settings` interface in [`src/types/index.ts`](src/types/index.ts).

### CUDA detection & compute type

On startup the sidecar probes CUDA via `torch.cuda.is_available()` and reports the result in the `ready` message. If `device = "cuda"` but CUDA is unavailable, the sidecar silently falls back to CPU with `int8` compute; the UI surfaces a warning.

`compute_type = "auto"` maps to:

- `cpu` → `int8`
- `cuda` → `float16`

Users can override this on the Model screen.

### Transcription queue

Implemented in `task_queue.py` as a `collections.deque` drained by a single worker thread. Recording can begin again while a previous transcription is still running — jobs are processed sequentially. Maximum depth is 10; if exceeded, the oldest unprocessed job is dropped with an error message.

## Tauri backend — Rust

### Responsibilities

- Spawn, monitor, and restart the Python sidecar process.
- Manage the system tray and main window.
- Register the global hotkey (platform-dependent — see below).
- Write transcription results to the clipboard.
- Trigger auto-paste (X11: `rdev`; Wayland: `ydotool`).
- Forward hotkey events to the sidecar over the WebSocket.

### Source layout

```
src-tauri/src/
├── main.rs           # Entry point
├── lib.rs            # Tauri setup, commands, tray, window
├── sidecar.rs        # Python process lifecycle
├── websocket.rs      # WebSocket client to the sidecar
├── tray.rs           # Tray icon and click handling
├── hotkey.rs         # Global shortcut registration (backend dispatch)
└── hotkey/
    ├── portal.rs         # Wayland — XDG GlobalShortcuts portal (ashpd)
    └── gnome_fallback.rs # Wayland — gsettings custom shortcut
```

### Plugins

```toml
tauri-plugin-global-shortcut      # X11 / macOS / Windows hotkey
tauri-plugin-clipboard-manager    # Clipboard writes
tauri-plugin-shell                # Sidecar management
tauri-plugin-positioner           # Tray-relative window positioning
tauri-plugin-opener               # Open external URLs / logs
tauri-plugin-single-instance      # Ensure one running instance (needed by GNOME fallback)
```

### Sidecar lifecycle

In production, `tauri.conf.json` declares the sidecar as an external binary:

```json
"bundle": { "externalBin": ["binaries/dictate-sidecar"] }
```

Tauri spawns it at app start with `--config <path>`. If the process exits unexpectedly, Tauri restarts it after a 2-second delay and emits `sidecar_restarted` to the frontend.

In development, the sidecar is normally run directly with `python main.py` — faster iteration, no PyInstaller rebuild.

## WebSocket message protocol

All messages are JSON with a `type` field. The TypeScript union lives in [`src/types/index.ts`](src/types/index.ts) (`SidecarMessage`).

**Tauri → Python (commands):**

```json
{ "type": "start_recording" }
{ "type": "stop_recording" }
{ "type": "toggle_recording" }
{ "type": "update_settings", "settings": { ... } }
{ "type": "get_status" }
{ "type": "shutdown" }
```

**Python → Tauri (events):**

```json
{ "type": "ready", "device": "cpu", "model": "small", "cuda_available": false, "cuda_version": "12.1", "session_type": "x11", "sidecar_version": "0.1.0" }
{ "type": "model_loading" }
{ "type": "model_ready", "load_time_ms": 3200 }
{ "type": "recording_started" }
{ "type": "recording_stopped" }
{ "type": "transcribing", "queue_depth": 1 }
{ "type": "transcription_complete", "text": "...", "duration_ms": 1430, "transcription_ms": 600, "confidence": 0.92, "detected_language": "en" }
{ "type": "transcription_empty" }
{ "type": "settings_saved" }
{ "type": "hotkey_mode", "mode": "tauri" | "evdev" | "none" }
{ "type": "error", "code": "MODEL_LOAD_FAILED", "message": "..." }
```

## Linux hotkey — backend selection

Global hotkeys on Linux are the most complex platform concern. Which backend is used depends on session type and compositor.

### Detection

`XDG_SESSION_TYPE` is read at startup (with `WAYLAND_DISPLAY` / `DISPLAY` as fallbacks) and reported in the `ready` message. The Rust side also exposes `get_hotkey_backend` as a Tauri command the frontend can query.

### Selection

```
Linux + Wayland:
    portal available?    → portal
    else GNOME?          → gnome-fallback
    else                 → unavailable (banner: bind manually)
Linux + X11:             → legacy (tauri-plugin-global-shortcut)
macOS / Windows:         → legacy
```

Portal availability is probed once per process via a blocking `zbus` introspect of `org.freedesktop.portal.Desktop` and cached in a `OnceLock`.

### Backend 1 — XDG GlobalShortcuts portal

Used on KDE Plasma 6+, Sway with `xdg-desktop-portal-wlr`, and sandboxed / Flatpak GNOME. Implemented in `src-tauri/src/hotkey/portal.rs` using [`ashpd`](https://docs.rs/ashpd).

- A single long-lived Tokio task owns the portal session, listens for `Activated` / `Deactivated` signals, and forwards them as `start_recording` / `stop_recording` over the WebSocket.
- The compositor (not the app) is the source of truth for the binding. The user confirms or overrides the shortcut in the compositor's UI.
- On portal v2 (GNOME 45+, KDE Plasma 6+), `Deactivated` fires on key release → true push-to-talk. On older portals the hotkey is press-only (toggle).
- Sessions are not persisted; the app creates a new one each launch.

### Backend 2 — GNOME `gsettings` fallback

Used on unsandboxed GNOME where the portal isn't exposed to host apps. Implemented in `src-tauri/src/hotkey/gnome_fallback.rs`.

- Writes a custom keybinding under `org.gnome.settings-daemon.plugins.media-keys.custom-keybinding` named "Dictate toggle", bound to the user's hotkey, with the command `<dictate binary> --toggle`.
- GNOME media-keys only deliver key-press events → the hotkey is inherently **toggle-only**. The UI banner reflects this.
- Because GNOME spawns the binary on every press, `tauri-plugin-single-instance` is used to prevent piling up app instances: on a second launch, the `single-instance` callback inspects `argv`, sees `--toggle`, and forwards a `toggle_recording` message to the running sidecar.

### Backend 3 — legacy (X11, macOS, Windows)

`tauri-plugin-global-shortcut` handles registration directly. Press → `start_recording`, release → `stop_recording`. True push-to-talk.

## Clipboard & auto-paste

When the Tauri shell receives `transcription_complete`, it writes the text to the clipboard via `tauri-plugin-clipboard-manager`. If autopaste is enabled, it then simulates Ctrl+V (or the configured paste shortcut):

- **X11**: `rdev` directly synthesizes keypresses.
- **Wayland**: shells out to `ydotool` (requires `ydotoold` running as a user systemd service — see README).
- **If `ydotoold` is unreachable**: the paste silently falls back to clipboard-only.

## Window & theme

The main window is frameless (`decorations: false`). The React UI paints its own title bar — see `src/components/layout/Header.tsx`. The entire header is a drag region except the three window-control buttons; double-click toggles maximize.

Theme auto mode watches the OS color scheme. On Linux this uses `org.freedesktop.portal.Settings` `ColorScheme`; on macOS/Windows it uses the `dark-light` crate. Theme changes apply live without restart.

## Error codes

| Code | Meaning | UI response |
|---|---|---|
| `MODEL_LOAD_FAILED` | Model files missing or corrupt | Show download prompt |
| `NO_MICROPHONE` | No input device | Show device list in error |
| `CUDA_UNAVAILABLE` | CUDA requested but not found | Silent fallback + warning badge |
| `SIDECAR_TIMEOUT` | Sidecar didn't connect in time | Retry button |
| `QUEUE_OVERFLOW` | Queue exceeded 10 items | Toast warning |
| `TRANSCRIPTION_FAILED` | faster-whisper threw | Toast error, continue |
| `HOTKEY_REGISTRATION_FAILED` | Backend refused the binding | Prompt for a different hotkey |
