# dictate

**Offline, privacy-first speech-to-text for your terminal.** Hold a global hotkey, speak, release — your words are transcribed locally via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and copied to your clipboard. Nothing leaves your machine.

A Python daemon with a Textual TUI for configuration, status, and history.

## Features

- **Global push-to-talk hotkey** — `ctrl+shift+d` by default.
- **100% offline** — faster-whisper runs on-device (first run downloads the model).
- **Auto-paste** — optional paste-at-cursor (X11/mac/Win: pynput; Wayland: ydotool).
- **History** — scrollable list of past transcriptions.
- **TUI for everything else** — `dictate tui` opens a terminal UI with live status, settings, and history.

## Install

```bash
pipx install dictate    # or: pip install --user dictate
```

Requires Python 3.11+ and `libportaudio2` on Linux.

## Quick start

```bash
# Run the daemon in one terminal (Ctrl+C to stop)
dictate

# In another terminal, open the config TUI
dictate tui
```

Hold `ctrl+shift+d` to record, release to transcribe. The transcription lands in your clipboard.

## Commands

| Command | What it does |
|---|---|
| `dictate` | Run the daemon (foreground). |
| `dictate tui` | Open the Textual TUI (requires a running daemon). |
| `dictate toggle` | Send SIGUSR1 — toggle recording. For Wayland compositor bindings. |
| `dictate start` / `dictate stop` | Same signal; for Sway/i3 `bindsym --release` pairs. |
| `dictate --version` | Print version. |

## Configuration

The daemon reads `~/.config/dictate/config.toml`. On first run it writes a fully-commented default. Edit by hand or use `dictate tui`. Changes take effect on `SIGHUP` (the TUI sends this automatically on save).

Structural changes (model size, device, compute type, mic) require a daemon restart — the TUI prompts you.

## Wayland setup

Wayland compositors don't expose a universal global-hotkey API, so you bind `dictate toggle` manually in your compositor's keyboard settings.

**KDE Plasma:** System Settings → Shortcuts → Add Application → Command: `dictate toggle`

**Sway / Hyprland:** add to config:
```
bindsym ctrl+shift+d exec dictate toggle
# For true push-to-talk (Sway):
# bindsym ctrl+shift+d exec dictate start
# bindsym --release ctrl+shift+d exec dictate stop
```

**GNOME:** Settings → Keyboard → Custom Shortcuts → Add: Command: `dictate toggle`

Auto-paste on Wayland requires `ydotool` + `ydotoold`. See the systemd unit example in [DEBUGGING.md](DEBUGGING.md).

## Run at login (systemd)

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

```bash
systemctl --user enable --now dictate
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design. TL;DR: one Python daemon + one Textual TUI, sharing state via files in XDG dirs + POSIX signals.

## License

[MIT](LICENSE) © 2026 Geoffrey Byers
