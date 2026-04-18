#!/usr/bin/env bash
# Build the dictate sidecar as a single-file binary with PyInstaller.
# Run from project root. Output: src-tauri/binaries/dictate-sidecar-<target-triple>
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SIDECAR="$ROOT/sidecar"
OUT="$ROOT/src-tauri/binaries"
mkdir -p "$OUT"
cd "$SIDECAR"
python3 -m pip install pyinstaller -q
python3 -m PyInstaller main.py \
  --name dictate-sidecar \
  --onefile \
  --distpath "$OUT" \
  --workpath "$ROOT/build/pyinstaller" \
  --specpath "$ROOT/build/pyinstaller" \
  --hidden-import faster_whisper \
  --hidden-import sounddevice
# PyInstaller outputs dictate-sidecar (no triple) when --onefile; Tauri expects dictate-sidecar-<triple>
TARGET=$(rustc --print host-tuple 2>/dev/null || echo "unknown")
if [[ -f "$OUT/dictate-sidecar" ]] && [[ ! -f "$OUT/dictate-sidecar-$TARGET" ]]; then
  mv "$OUT/dictate-sidecar" "$OUT/dictate-sidecar-$TARGET"
fi
echo "Sidecar built: $OUT/dictate-sidecar-$TARGET"
