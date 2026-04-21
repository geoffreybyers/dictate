# Debugging PrivateDictate

## Logs

Daemon logs to `~/.local/share/private-dictate/private-dictate.log` (rotating, 10 MB × 3 by default; tune in `[logs]`).

```bash
tail -f ~/.local/share/private-dictate/private-dictate.log
```

Set `logs.level = "debug"` for verbose output.

## Runtime state

```bash
cat ~/.cache/private-dictate/status.json | jq
```

## Verbose daemon (foreground)

Run the daemon from a terminal to see stderr too:

```bash
private-dictate 2>&1 | tee /tmp/private-dictate.log
```

## Wayland auto-paste (ydotool)

If auto-paste silently falls back to clipboard-only:

```bash
# Check ydotoold
systemctl --user status ydotoold.service

# Test ydotool by hand
echo "ctrl+v" | ydotool key ctrl+v
```

Reference systemd unit for `ydotoold`:

```ini
[Unit]
Description=ydotool user daemon

[Service]
Type=simple
ExecStart=/usr/bin/ydotoold --socket-path=%t/.ydotool_socket --socket-own=%U:%G
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
```

## No microphone / no device

`~/.cache/private-dictate/status.json.last_error` will contain the detail. Fix the device in `[audio].microphone` or leave it blank for the system default. Run `python -c "import sounddevice; print(sounddevice.query_devices())"` to list devices.

## Tests

```bash
pytest tests/unit -v
pytest tests/tui -v
pytest tests/integration -v
```
