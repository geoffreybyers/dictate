# dictate v2 — replace GUI with TUI + daemon

**Status:** design approved, ready for planning
**Date:** 2026-04-18
**Author:** Geoffrey Byers (with Claude)

## Motivation

The current dictate app is a Tauri (Rust) shell + React/Vite/TypeScript/Tailwind frontend + Python sidecar communicating over a local WebSocket. For a tool whose runtime is "hold a global hotkey, speak, release, paste," that stack is disproportionate. The frontend is almost entirely a settings surface; the Rust layer spends most of its code on Wayland portal plumbing, single-instance GNOME fallback, auto-paste, and sidecar lifecycle management.

Goal: rebuild as a single-language Python tool. Keep the core UX (hotkey → transcribe → clipboard/paste) and the discoverability of a full settings surface, shed everything else.

Non-goals:
- Preserving existing installations (no users yet, clean break).
- Wayland push-to-talk parity (portal integration is the costliest line-per-value code in the current repo; we accept toggle-mode on Wayland as an explicit trade).
- Cross-language IPC protocols. The new app has exactly one language boundary: Python and TOML.

## Architecture

Two Python processes. No sockets, no RPC, no WebSocket.

### Processes

**`dictate` (daemon)** — long-running foreground Python process. Owns:
- Faster-whisper model load
- Microphone capture (sounddevice / PortAudio)
- Hotkey listener (pynput)
- Transcription queue (single worker, deque, max depth 10)
- Clipboard writes (pyperclip)
- Auto-paste (pynput on X11/mac/Win, ydotool shell-out on Wayland)
- History append, status writes, log output

Reloads config on `SIGHUP`. Toggles recording on `SIGUSR1`. Graceful shutdown on `SIGTERM` / `SIGINT`.

**`dictate tui`** — short-lived Textual app. Owns only rendering.
- Reads `config.toml`, `status.json`, `history.jsonl`.
- Polls `status.json` at 10 Hz for the live footer.
- Writes `config.toml` atomically on Save, then sends `SIGHUP` to the daemon.
- Exits when the user quits (`q`).

### Shared state — files in XDG dirs

| File | Writer | Readers | Purpose |
|---|---|---|---|
| `~/.config/dictate/config.toml` | TUI, user | daemon | Settings. Hand-editable. Commented. |
| `~/.cache/dictate/status.json` | daemon | TUI, user scripts | Runtime state: `{state, model_loaded, recording, queue_depth, last_error, pid, uptime_s}`. Rewritten ~5 Hz idle, 10 Hz active. |
| `~/.local/share/dictate/history.jsonl` | daemon | TUI | One JSON line per transcription. Append-only. Rotated at `history.limit`. |
| `~/.local/share/dictate/dictate.log` | daemon | user, TUI | Rotating file log. |
| `~/.cache/dictate/dictate.pid` | daemon | TUI, `dictate toggle` | PID + start timestamp. |

### Why this shape

- Files + POSIX signals are infrastructure the OS gives us for free. No protocol to version, no handshake to time out, no port to negotiate.
- TUI and daemon are fully decoupled. Worst-case interaction is a stale status file, which self-corrects in 200 ms.
- Anyone can inspect or script around state with `cat` / `jq`. Ambient indicators (waybar / polybar / i3status widgets) are ~10 lines of user config reading `status.json` directly.
- "Is the daemon running?" = PID alive and wrote status within N seconds. No heartbeats, no retries.

### Accepted tradeoff — restart on structural config changes

Config changes that require a model or device swap (`model.size`, `model.device`, `model.compute_type`, `model.cache_dir`, `audio.microphone`) need a daemon restart. The TUI surfaces this: on Save with one of these fields dirty, show a modal "this change requires restart. [Restart daemon] [Cancel]." Choosing Restart sends `SIGTERM` to the daemon; the user restarts it themselves (the TUI does not spawn daemons — see Lifecycle).

Not slick, but honest. Alternatives (hot-reload every component, double-buffer model loads) would reintroduce the complexity we're trying to shed.

## Commands and lifecycle

Tiny command surface. Everything else is the config file.

```
dictate                 # Run the daemon in the foreground. Ctrl+C quits.
dictate tui             # Launch the TUI. Errors if no daemon is running.
dictate toggle          # Send SIGUSR1 (toggle) to the daemon. Wayland compositor binding.
dictate start           # Send SIGUSR1 with START semantics (for Sway --release bindings).
dictate stop            # Send SIGUSR1 with STOP semantics.
dictate --version
dictate --help
```

### Design choices

- **`dictate` with no args is the daemon**, not the TUI. The daemon is the thing that has to be running for the tool to work at all. New users type `dictate`, see `listening for [ctrl+shift+d]…`, and immediately understand the model.
- **`dictate tui` refuses to auto-start the daemon.** If the daemon isn't running, the TUI prints `no dictate daemon running. start one with 'dictate' in another terminal, or see README for systemd setup.` This is deliberate: zero daemonization code, zero "is the daemon mine or adopted" ambiguity. Future work may reconsider (see Future Work).
- **`toggle` / `start` / `stop` are one signal family.** One `SIGUSR1` handler in the daemon. `start` / `stop` allow Sway/i3-compatible compositors to bind press and release separately and recover true push-to-talk.
- **No `dictate config set` subcommand.** Config is set by editing `config.toml` or saving in the TUI. Two ways, not three.
- **No `install` / `uninstall` / `service` subcommands.** README shows the systemd unit file; `systemctl --user enable --now dictate` is copy-paste.

### Daemon main loop

```
  user runs `dictate`
         │
         ▼
  write PID file
  load model                  ◄── config reloaded on SIGHUP
  start hotkey listener
         │
         ▼
  ┌────────────────────────────────┐
  │ main loop                      │
  │  on hotkey press:              │
  │      recorder.start()          │
  │      write status: recording   │
  │  on hotkey release:            │
  │      audio = recorder.stop()   │
  │      queue.enqueue(audio)      │
  │  on SIGUSR1:                   │
  │      hotkey.external_toggle()  │
  │  on SIGHUP:                    │
  │      config.reload()           │
  │      if structural change:     │
  │          status.needs_restart  │
  │  on SIGTERM / Ctrl+C:          │
  │      drain queue (5 s deadline)│
  │      clean exit, rm PID        │
  └────────────────────────────────┘
```

Worker thread drains the transcription queue. Recording can restart while a prior transcription runs.

### Signal semantics

- **`SIGHUP`** — reload config. Structural changes (model/device) set `needs_restart=true` in `status.json`; don't attempt hot-swap.
- **`SIGUSR1`** — respects `hotkey.mode`:
  - `mode = "toggle"` → flip recording state.
  - `mode = "hold"` → treat as toggle fallback (for Wayland `dictate toggle` users who didn't change their config).
- **`SIGUSR2`** — rotate log (reserved; implement if the rotating-handler isn't sufficient).
- **`SIGTERM` / `SIGINT`** — drain queue (5 s deadline), clean shutdown, remove PID file.

## TUI structure

Keyboard-driven, Textual-rendered. Sidebar + content + live footer.

```
┌──────────────────────────────────────────────────────┐
│ dictate                                    q Quit    │  top bar
├────────────┬─────────────────────────────────────────┤
│ ▸ Status    │                                         │
│   Settings  │                                         │
│   History   │     Content (varies by screen)          │
│             │                                         │
│             │                                         │
├────────────┴─────────────────────────────────────────┤
│ ● Recording…   queue: 1       model: small · cpu     │  footer (live)
└──────────────────────────────────────────────────────┘
```

### Navigation

- `↑` / `↓` or `j` / `k` — move within sidebar or focused list.
- `Tab` / `Shift+Tab` — move focus between panes.
- `Enter` — activate / edit.
- `s` Settings, `h` History, `/` focus search (History), `q` quit.
- `?` — help overlay listing every binding.
- `Ctrl+s` — save (Settings, when dirty).
- `Esc` — discard pending edits / close overlay.

### Screens

**Status** (default on launch)
- Large state indicator: Idle / Recording / Transcribing / Error.
- Current hotkey, current model + device, daemon uptime.
- Last transcription preview (one line) with `c` to copy.
- Suitable for "leave open in a spare pane for ambient awareness."

**Settings**
- One flat scrollable form. No sub-tabs.
- Section headers: Hotkey / Model / Transcription / Audio / History / Logs / TUI.
- Each row: label + control (toggle, select, text input, hotkey-capture widget).
- Save/Discard bar slides up from the bottom when any field is dirty (preserves the current app's explicit-save model — no surprise writes).
- Structural changes (model/device) trigger a restart modal on Save.

**History**
- Scrollable list grouped by day (Today / Yesterday / absolute date).
- Each row: timestamp, full transcription (wrapped), optional metadata line (confidence · duration · language) when `transcription.verbose_metadata = true`.
- Per-row actions: `c` copy, `d` delete, `Enter` copy-and-preview.
- `/` to filter by substring.
- Clear-all at top (confirm prompt).

### Status footer

Always visible across screens. Reads `status.json` at 10 Hz.

- Idle: `idle · hold [ctrl+shift+d] to record · model: small · cpu`
- Recording: `● Recording… · press release to stop`
- Transcribing: `⏳ Transcribing… · queue: 2`
- Copied: `✓ copied · 1.4s · 92%` (ephemeral, 3 s)
- Error: `⚠ error: <message>` (sticky until acknowledged with `Esc`)

### Theme

Textual dark / light built-in. `tui.theme = "auto" | "dark" | "light"`. Auto follows the terminal's declared background (Textual exposes this). No OS color-scheme integration — wrong layer for a terminal tool.

### State flow

```
user edits a field ─► in-memory form state (dirty)
                  ─► Save ─► write config.toml atomically (temp + rename)
                          ─► send SIGHUP to daemon
                          ─► daemon reloads
                          ─► if structural change:
                                status.needs_restart = true
                                TUI modal: "Restart daemon?"
                                on yes: SIGTERM daemon
                                        user restarts it themselves
```

## Settings schema — `config.toml`

One file, hand-editable, commented. TUI and daemon read/write the same format. Atomic writes (temp + rename) prevent corruption on kill mid-save.

```toml
# dictate config — see `dictate tui` for an interactive editor.
# Daemon reloads this file on SIGHUP (the TUI sends it automatically
# on save). Fields marked [restart] require `dictate` to be restarted.

[hotkey]
# A single key or modifier+key combo. Examples: "F9", "ctrl+shift+space".
# Plain space requires a modifier.
binding = "ctrl+shift+d"

# Behavior when the compositor only delivers key-press events (Wayland via
# `dictate toggle`). "toggle" is the one reliable path everywhere.
# "hold" only works on X11/macOS/Windows and Sway with --release bindings.
mode = "hold"  # "hold" | "toggle"

[model]
size          = "small"     # "small" | "medium"             [restart]
device        = "auto"      # "auto" | "cpu" | "cuda"        [restart]
compute_type  = "auto"      # "auto" | "int8" | "float16" | "int8_float16"
cache_dir     = ""          # empty → ~/.cache/dictate/models

[transcription]
language         = "auto"   # "auto" or ISO code, e.g. "en", "es"
max_seconds      = 180      # hard cap on a single recording
autopaste        = true     # clipboard + simulate paste shortcut
paste_shortcut   = "ctrl+v" # "ctrl+v" | "ctrl+shift+v" — ignored if autopaste=false
verbose_metadata = false    # include confidence / duration / language in
                            # TUI rows and status footer

[audio]
# empty = system default. Run `dictate --list-mics` to see names.
microphone = ""

[history]
save  = true
limit = 100                 # rotate when exceeded; oldest dropped

[logs]
level       = "info"        # "debug" | "info" | "warn" | "error"
max_size_mb = 10

[tui]
theme = "auto"              # "auto" | "dark" | "light"
```

### Consolidation from the current schema

| Current | New | Rationale |
|---|---|---|
| General: App Language + Dictation Language | `transcription.language` only | App language is English-only for v1. TUI copy is minimal; translation burden unjustified. |
| Advanced: Show confidence / Show timing / Show detected language | `transcription.verbose_metadata` | Three booleans collapse to one. |
| General: save_history / history_limit / "Clear All" | `history.save` + `history.limit` + `c` action | Button becomes a TUI action. |
| Window width / height / x / y | *removed* | No window. |
| `first_run` | *removed* | No welcome banner. |
| Tauri / platform / session_type / version info | *removed* | `dictate --version` and the log cover this. |
| Model cache dir read-only + copy button | `model.cache_dir` editable | Empty string = default. Edit to relocate. |

### Validation

Daemon validates on load. Bad fields fall back to defaults, log a warning, and write a structured `last_error` into `status.json` so the TUI can surface it. The daemon never refuses to start over a bad config — too easy to lock a user out of fixing it.

### First run

If `config.toml` doesn't exist on daemon startup, the daemon writes the full commented default (exactly the block shown above) to `~/.config/dictate/config.toml` and logs `first-run config created at <path>`. Then continues normally. First-run model download is handled by `faster-whisper` itself on first transcription — the daemon writes `status.state = "downloading_model"` while it happens so the TUI can show progress.

## Daemon internals

### Module layout

```
dictate/
├── __main__.py         # python -m dictate → daemon entry
├── cli.py              # argparse, dispatch to daemon/tui/toggle/start/stop
├── daemon.py           # Main loop, signal handlers, lifecycle
├── config.py           # TOML load/save, validation, defaults
├── hotkey.py           # pynput listener, modifier parsing, toggle/hold state
├── recorder.py         # sounddevice mic capture, ring buffer
├── transcriber.py      # faster-whisper wrapper, model load + warm call
├── queue.py            # Single-worker transcription queue (deque + thread)
├── clipboard.py        # pyperclip wrapper
├── paste.py            # Auto-paste: pynput on X11/mac/Win, ydotool on Wayland
├── state.py            # status.json / history.jsonl / PID — atomic writes
├── log.py              # Rotating file logger
└── tui/
    ├── __init__.py
    ├── app.py          # Textual App + routing
    ├── status.py       # Status screen
    ├── settings.py     # Settings screen (flat form + save bar)
    └── history.py      # History screen
```

### Module contracts (selected)

- `hotkey.HotkeyListener(binding: str, mode: "hold"|"toggle", on_start, on_stop)` — owns its threads. `start()` / `stop()`. `external_toggle()` for SIGUSR1.
- `recorder.Recorder(sample_rate=16000, mic: str|None)` — `start()`, `stop() -> np.ndarray`. Typed errors for "no mic" / "mic disappeared" / "device-in-use."
- `transcriber.Transcriber(size, device, compute_type)` — `transcribe(audio) -> TranscriptionResult{text, duration_ms, language, confidence}`. Synchronous. Loaded once at startup.
- `queue.TranscriptionQueue(worker_fn, max_depth=10)` — `enqueue(audio)`. Drops oldest on overflow, emits typed error.
- `state.StateWriter` — `write_status(...)`, `append_history(entry)`, `write_pid()`, `clear_pid()`. All writes atomic (temp + rename).

### Transcription flow

```
hotkey press ──► recorder.start()    ──► status: recording
hotkey release ──► audio = recorder.stop()
                   queue.enqueue(audio) ──► status: transcribing, queue: N
                                              │
                                    worker thread:
                                              ▼
                                      transcriber.transcribe(audio)
                                              │
                            ┌─────────────────┼──────────────────┐
                            ▼                 ▼                  ▼
                        clipboard        auto-paste         history.append
                        .copy(text)      if enabled         status: copied
```

### Error handling — where it lives

- **Recoverable** (bad audio, transcription failure, queue overflow, autopaste unavailable): logged, `status.last_error` set, daemon continues.
- **Unrecoverable** (model load fails, no mic at all, mic disappears mid-stream): logged, `status.last_error` set, daemon stays alive in a "broken" state so the TUI can surface it. **Exiting on error is wrong for a tool bound to a global hotkey** — the user has no feedback channel.
- **Config broken** (invalid TOML): daemon logs, falls back to in-memory defaults, writes `last_error`. Doesn't exit.

### Dependencies we're trusting

- **pynput** keeps working across X11 / macOS / Windows. It does today; risk is low.
- **pyperclip** finds an available clipboard backend on first touch (same as the existing CLI).
- **sounddevice + PortAudio** handles device hotplug gracefully. If not, we re-init the recorder on mic errors.

## Platform support

| Platform | Status | Notes |
|---|---|---|
| Linux X11 | Primary | pynput push-to-talk, pyperclip clipboard, pynput auto-paste. |
| Linux Wayland | Supported, toggle-only | User binds `dictate toggle` in their compositor's keyboard settings. Sway with `bindsym --release` can recover push-to-talk via `dictate start` / `dictate stop`. Auto-paste via `ydotool` (requires `ydotoold` running — same as today). |
| macOS | Supported | Requires Microphone + Accessibility permissions. pynput handles hotkey and auto-paste. |
| Windows | Supported | pynput handles everything. |

No portal code, no gsettings fallback code, no single-instance plumbing. README documents the one-time compositor-binding step for Wayland users with exact copy for common compositors (KDE Plasma, GNOME, Sway, Hyprland).

## Packaging and distribution

- **Primary: `pipx install dictate` from PyPI.** Terminal-tool canonical. Pulls in faster-whisper, CTranslate2, pynput, textual, pyperclip, sounddevice.
- **Secondary: PyInstaller single binary in GitHub Releases.** Same pipeline as the existing sidecar. For users who don't want to install Python. Not day-one.
- **What goes away**: no `.deb`, `.AppImage`, `.msi`, `.dmg`. Those were needed for Tauri's bundle. A terminal tool doesn't need them.
- **systemd unit**: copy-paste block in README, not packaged.

```ini
# ~/.config/systemd/user/dictate.service
[Unit]
Description=dictate — offline speech-to-text daemon

[Service]
Type=simple
ExecStart=%h/.local/bin/dictate
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
```

Enable: `systemctl --user enable --now dictate`.

## Testing approach

### Unit tests (pytest)

- `config.py` — TOML parse, validation, defaults, bad-field fallback, round-trip.
- `queue.py` — enqueue/dequeue, overflow drops oldest, worker exceptions don't kill the thread.
- `state.py` — atomic writes, history JSONL append, status.json format stability.
- `hotkey.py` — modifier parsing, toggle/hold state machine (separate from pynput listener).
- `paste.py` — platform dispatch picks correct backend; backend errors fall back to clipboard-only.

### TUI tests (Textual pilot)

Snapshot tests per screen. Event simulation via `app.run_test()` pilot. Example:

```python
async def test_settings_save_sends_sighup(tmp_path, fake_daemon):
    app = DictateTUI(config_path=tmp_path/"config.toml")
    async with app.run_test() as pilot:
        await pilot.press("tab", "tab", "enter")      # navigate to hotkey field
        await pilot.type("f9")
        await pilot.press("ctrl+s")                    # save
        assert fake_daemon.received_signals == [signal.SIGHUP]
        assert "f9" in (tmp_path/"config.toml").read_text()
```

### Daemon integration tests (subprocess + signals)

Start the daemon in a subprocess with a test config; send signals; assert on log lines and status.json contents.

- `SIGHUP` with a modified config → reloaded.
- `SIGUSR1` → recording state flips (recorder mocked to return silence).
- `SIGTERM` → PID removed, exit code 0.

Linux-only in CI.

### Not automated

- Real microphone capture. `test.wav` fixture feeds `transcriber.transcribe()` directly for correctness smoke test.
- Global-hotkey registration (no display in CI). Manual pre-release checklist.
- Wayland portal / compositor binding. Users own this.

### CI

GitHub Actions. Linux for daemon + integration suite. TUI and unit tests also on macOS + Windows. `pytest` + `pytest-asyncio` + Textual pilot. No heavy harness.

## Deletions

Explicit list so scope is clear.

```
src/                           # React frontend
src-tauri/                     # Tauri/Rust layer
sidecar/                       # Old sidecar — folds into new dictate/ package
dist/                          # Built frontend output
public/                        # Frontend assets
node_modules/                  # (gitignored anyway)
index.html
package.json, package-lock.json
vite.config.ts
tsconfig.json, tsconfig.node.json
tailwind.config.js, postcss.config.js
UI_SPEC.md                     # replaced by TUI_SPEC.md or folded into README
scripts/build-sidecar.sh
test.wav                       # keep if used for unit-test fixture; remove if GUI-only
```

Cargo.lock, Tauri icons: gone with `src-tauri/`.

**The old `dictate/` CLI**: replaced. New package lives at `dictate/` (same name, new contents). No reason to keep two CLI entry points.

**`ARCHITECTURE.md` / `DEBUGGING.md` / `CONTRIBUTING.md` / `SECURITY.md`**: keep but rewrite — they describe the old architecture. ARCHITECTURE.md is a full rewrite; the others get light edits.

## Decisions explicitly taken

| Decision | Choice | Rationale |
|---|---|---|
| Motivation | Maintenance burden + simplicity | User stated |
| Language boundary | Python only | Shed Rust + TypeScript in one pass |
| Interface | Textual TUI, separate process | Discoverable like the old GUI, cheap in terminal |
| IPC | Files + POSIX signals | No protocol to version |
| Wayland | Graceful degradation (user binds compositor shortcut) | Portal code is highest-cost-per-value; recoverable |
| Daemon lifecycle | User-managed (`dictate` foreground); systemd unit in docs | Zero daemonization code |
| Scope | Status + Settings + History TUI screens (Approach 3) | Flatten config screens; keep interactive surfaces as screens |
| Tray icon | None | `status.json` + waybar covers ambient-indicator use case |
| Migration | None required (no users) | Clean break |
| Packaging | pipx primary, PyInstaller secondary | Canonical for Python terminal tools |
| Default hotkey | `ctrl+shift+d` | Low collision across shell / browser / IDE |
| Default `max_seconds` | 180 | User preference |
| Default `history.limit` | 100 | User preference |

## Future work (documented, not in scope now)

- **Implicit daemon lifecycle (option B from brainstorm).** `dictate tui` auto-spawns a detached daemon if none is running; `dictate stop` kills it. Requires correct double-fork, PID races, log redirection, tty detachment. Revisit when the foreground-only model's ergonomics become friction.
- **Wayland portal push-to-talk (option A from brainstorm).** Python re-implementation of the ashpd-based portal integration in `src-tauri/src/hotkey/portal.rs`. Would restore true push-to-talk on KDE Plasma 6+ / Sway-with-portal / sandboxed GNOME. Bolt-on module; the daemon's toggle interface is stable.
- **Tray icon.** Optional module reading `status.json`. Cross-platform via pystray or a native alternative.
- **Single PyInstaller binary release.** For users who don't want Python on their system. Pipeline exists from the current sidecar build.
- **App-language localization.** Currently English-only.

## Out of scope

- Streaming / partial transcription results.
- Non-whisper backends.
- Cloud sync of history or settings.
- Multi-instance (per-user-session) operation.
- A web UI or mobile companion.
