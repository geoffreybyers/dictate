"""CLI dispatch. `dictate` alone = daemon; subcommands for TUI, signals."""
from __future__ import annotations

import argparse
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from dictate import __version__, paths
from dictate.daemon import Daemon


def _read_pid() -> Optional[int]:
    pid_path = paths.cache_dir() / "dictate.pid"
    if not pid_path.exists():
        return None
    try:
        pid = int(pid_path.read_text().splitlines()[0])
    except (ValueError, IndexError):
        return None
    # Is the process still alive?
    try:
        os.kill(pid, 0)
    except OSError:
        return None
    return pid


def _signal_daemon(sig: int) -> int:
    pid = _read_pid()
    if pid is None:
        print("no dictate daemon running. start one with 'dictate' in another terminal.",
              file=sys.stderr)
        return 1
    try:
        os.kill(pid, sig)
    except OSError as e:
        print(f"failed to signal daemon (pid={pid}): {e}", file=sys.stderr)
        return 1
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="dictate", description="Offline speech-to-text.")
    parser.add_argument("--version", action="store_true")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("tui", help="Launch the Textual TUI (requires a running daemon).")
    sub.add_parser("toggle", help="Send toggle (SIGUSR1) to the running daemon.")
    sub.add_parser("start", help="Send start signal (SIGUSR1) — Sway press bindings.")
    sub.add_parser("stop", help="Send stop signal (SIGUSR1) — Sway release bindings.")

    args = parser.parse_args(argv)

    if args.version:
        print(f"dictate {__version__}")
        return 0

    if args.cmd is None:
        return Daemon().run()
    if args.cmd == "tui":
        if _read_pid() is None:
            print("no dictate daemon running. start one with 'dictate' in another terminal, "
                  "or see README for systemd setup.", file=sys.stderr)
            return 1
        from dictate.tui.app import run_tui
        return run_tui()
    if args.cmd in {"toggle", "start", "stop"}:
        return _signal_daemon(signal.SIGUSR1)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
