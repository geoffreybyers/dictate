# dictate

**Privacy-first, offline speech-to-text for your desktop.** Hold a global hotkey, speak, release — your words are transcribed locally via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and copied to the clipboard. No audio or text ever leaves your machine.

![status: early development](https://img.shields.io/badge/status-early%20development-orange)
![license: MIT](https://img.shields.io/badge/license-MIT-blue)

---

## Features

- **Global push-to-talk hotkey** — hold, speak, release. Works from any app.
- **100% local** — audio is captured, transcribed, and discarded on your machine. Nothing is sent to any server.
- **Whisper, offline** — first run downloads the model; after that, you're fully offline.
- **Auto-paste** (optional) — paste the transcription directly at the cursor instead of just copying.
- **Transcription history** — revisit, copy, or delete past transcriptions.
- **CPU or NVIDIA CUDA** — picks the fastest backend available and falls back gracefully.
- **X11 and Wayland** on Linux, with a dedicated portal / GNOME fallback for global hotkeys.

## Platform support

| Platform | Status | Notes |
|---|---|---|
| Linux X11 | ✅ Primary development target | Global hotkey via `tauri-plugin-global-shortcut` |
| Linux Wayland (GNOME) | ✅ | Uses `gsettings` fallback — hotkey is toggle-only (press to start, press to stop). Requires `ydotool` for auto-paste. |
| Linux Wayland (KDE, Sway) | ✅ | Uses XDG GlobalShortcuts portal (push-to-talk on portal v2 compositors). Requires `ydotool` for auto-paste. |
| macOS | 🟡 Experimental | Requires Microphone + Accessibility permissions. Not actively tested. |
| Windows | 🟡 Experimental | Requires Visual C++ Redistributable. Not actively tested. |

## Requirements

- **Node.js** 20+
- **Rust** stable (current toolchain)
- **Python** 3.11+ for the sidecar
- **System audio library** — Linux: `libportaudio2` (`sudo apt install libportaudio2`)
- **Optional CUDA** — NVIDIA GPU with a recent CUDA runtime for faster inference
- **Optional (Wayland)** — `ydotool` + `ydotoold` for auto-paste

## Quick start (from source)

There are two processes: the Tauri app and the Python sidecar. In development you run them separately.

```bash
# 1. Clone
git clone https://github.com/geoffreybyers/dictate.git
cd dictate

# 2. Install frontend + Tauri deps
npm install

# 3. Install sidecar Python deps
cd sidecar
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd ..

# 4. Run (launches both — Tauri spawns the sidecar)
npm run tauri dev
```

The first launch downloads a Whisper model (~500 MB for `small`, ~1.5 GB for `medium`) into the app config directory. Subsequent launches are fully offline.

## Production build

```bash
# 1. Package the Python sidecar as a single binary
./scripts/build-sidecar.sh

# 2. Build the Tauri bundle
npm run tauri build
```

The bundled sidecar is placed at `src-tauri/binaries/dictate-sidecar` and embedded in the Tauri output. Prebuilt release binaries (AppImage, `.deb`, etc.) are planned but not yet published — for now, build from source.

## Linux / Wayland setup

### Global hotkey

Global hotkeys on Wayland go through one of two backends, chosen automatically at startup. The app surfaces which one is active in the settings panel:

- **XDG GlobalShortcuts portal** — KDE Plasma 6+, Sway with `xdg-desktop-portal-wlr`, or sandboxed GNOME. The compositor prompts you to confirm the binding. On portal v2 compositors you get true push-to-talk.
- **GNOME `gsettings` fallback** — unsandboxed GNOME. Registers a custom keyboard shortcut under *Settings → Keyboard → Custom Shortcuts* as "Dictate toggle". GNOME only delivers key-press events, so the hotkey is **toggle mode** — press once to start, press again to stop.

### Auto-paste

On X11, auto-paste uses the built-in `rdev` simulator. On Wayland there is no cross-compositor virtual-keyboard protocol, so dictate shells out to [`ydotool`](https://github.com/ReimuNotMoe/ydotool). One-time setup:

```bash
sudo apt install ydotool ydotoold      # Debian/Ubuntu — substitute for other distros

# If /dev/uinput isn't already accessible:
# sudo setfacl -m u:$USER:rw /dev/uinput

# Enable the user daemon:
cat > ~/.config/systemd/user/ydotoold.service <<'EOF'
[Unit]
Description=ydotool user daemon (virtual input for Wayland auto-paste)

[Service]
Type=simple
ExecStart=/usr/bin/ydotoold --socket-path=%t/.ydotool_socket --socket-own=%U:%G
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now ydotoold.service
```

If `ydotoold` isn't running, auto-paste silently falls back to clipboard-only — the text is copied, you just paste it yourself.

## Also in this repo

- **`dictate/`** — the original standalone Python CLI that predates the desktop app. Kept for users who prefer a terminal tool. See [`dictate/README.md`](dictate/README.md).

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — process model, Tauri ↔ sidecar WebSocket protocol, Linux hotkey backend selection.
- [UI_SPEC.md](UI_SPEC.md) — window layout, nav structure, per-screen settings.
- [DEBUGGING.md](DEBUGGING.md) — logs, DevTools, verbose flags.
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to propose changes.
- [SECURITY.md](SECURITY.md) — reporting vulnerabilities; privacy posture.

## License

[MIT](LICENSE) © 2026 Geoffrey Byers
