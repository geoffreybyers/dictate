# PrivateDictate

**Offline, privacy-first speech-to-text for your terminal.** Hold a global hotkey, speak, release — your words are transcribed locally via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and copied to your clipboard. Nothing leaves your machine.

A Python daemon with a Textual TUI for configuration, status, and history.

## Features

- **Global push-to-talk hotkey** — `ctrl+shift+d` by default on X11, macOS, and Windows. On Wayland, bind `private-dictate toggle` in your desktop's keyboard settings (see [Wayland setup](#wayland-setup)).
- **100% offline** — faster-whisper runs on-device (first run downloads the model).
- **Auto-paste** — optional paste-at-cursor (X11/mac/Win: pynput; Wayland: ydotool).
- **History** — scrollable list of past transcriptions.
- **TUI for everything else** — `private-dictate tui` opens a terminal UI with live status, settings, and history.

## Install

```bash
pipx install private-dictate    # or: pip install --user private-dictate
```

Requires Python 3.11+ and `libportaudio2` on Linux.

## Quick start

```bash
# Run the daemon in one terminal (Ctrl+C to stop)
private-dictate

# In another terminal, open the config TUI
private-dictate tui
```

Hold `ctrl+shift+d` to record, release to transcribe. The transcription lands in your clipboard.

> **Wayland users:** the in-process hotkey listener can't grab keys globally on Wayland. Follow [Wayland setup](#wayland-setup) to bind `private-dictate toggle` in your desktop environment instead. The `[hotkey]` block in `config.toml` has no effect on Wayland.

## Commands

| Command | What it does |
|---|---|
| `private-dictate` | Run the daemon (foreground). |
| `private-dictate tui` | Open the Textual TUI (requires a running daemon). |
| `private-dictate toggle` | Send SIGUSR1 — toggle recording. For Wayland compositor bindings. |
| `private-dictate start` / `private-dictate stop` | Same signal; for Sway/i3 `bindsym --release` pairs. |
| `private-dictate --version` | Print version. |

## Configuration

The daemon reads `~/.config/private-dictate/config.toml`. On first run it writes a fully-commented default. Edit by hand or use `private-dictate tui`. Changes take effect on `SIGHUP` (the TUI sends this automatically on save).

Structural changes (model size, device, compute type, mic) require a daemon restart — the TUI prompts you.

## Wayland setup

Wayland doesn't allow applications to grab keys globally — that's a security feature of the protocol. So the daemon's own hotkey listener is a no-op on Wayland, and the `[hotkey]` block in `config.toml` is ignored. Instead, bind `private-dictate toggle` in your desktop environment's keyboard settings: the DE receives the key and invokes the CLI, which signals the daemon via SIGUSR1.

**GNOME:** Settings → Keyboard → View and Customize Shortcuts → Custom Shortcuts → Add
- Name: `PrivateDictate toggle`
- Command: `private-dictate toggle` (or the absolute path, e.g. `/home/you/.local/bin/private-dictate toggle`)
- Shortcut: Ctrl+Shift+D (or whatever you prefer)

**KDE Plasma:** System Settings → Shortcuts → Add Application → Command: `private-dictate toggle`

**Sway / Hyprland:** add to config:
```
bindsym ctrl+shift+d exec private-dictate toggle
# For true push-to-talk (Sway):
# bindsym ctrl+shift+d exec private-dictate start
# bindsym --release ctrl+shift+d exec private-dictate stop
```

Auto-paste on Wayland requires `ydotool` + `ydotoold`. See the systemd unit example in [DEBUGGING.md](DEBUGGING.md).

> **Tip:** if you installed via `pipx`/`pip --user`, the binary is at `~/.local/bin/private-dictate`. If you're running from a project venv, use the full path to `<project>/.venv/bin/private-dictate` — DE shortcut commands don't inherit your shell's PATH.

## Run at login (systemd)

```ini
# ~/.config/systemd/user/private-dictate.service
[Unit]
Description=PrivateDictate — offline speech-to-text daemon

[Service]
Type=simple
ExecStart=%h/.local/bin/private-dictate
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now private-dictate
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design. TL;DR: one Python daemon + one Textual TUI, sharing state via files in XDG dirs + POSIX signals.

## License

[MIT](LICENSE) © 2026 Geoffrey Byers
