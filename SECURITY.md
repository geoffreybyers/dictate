# Security

PrivateDictate processes audio locally — nothing leaves your machine by default. Please report security issues privately to the maintainer (see README for contact) rather than opening a public GitHub issue.

## Threat model

- All audio capture, transcription, and clipboard activity happens on the local machine.
- The daemon writes config/status/history/log files inside your XDG dirs.
- Auto-paste simulates keyboard input into whatever app has focus at the time the transcription completes. Be aware when a secure field (password manager, lock screen) is focused.
