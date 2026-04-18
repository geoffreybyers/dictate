"""pyperclip wrapper with error handling."""

import shutil
import sys

import pyperclip


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard. Returns True on success, False on failure."""
    if sys.platform == "linux":
        if not shutil.which("xclip") and not shutil.which("xdotool"):
            print(
                "Clipboard on Linux requires xclip or xdotool. Install with:\n  sudo apt install xclip"
            )
            return False
    try:
        pyperclip.copy(text)
        return True
    except Exception as e:
        print(f"Clipboard error: {e}")
        return False
