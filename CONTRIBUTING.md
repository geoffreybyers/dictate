# Contributing to dictate

Thanks for your interest. dictate is a small early-stage project — contributions of all sizes are welcome.

## Before you start

- For anything non-trivial, **please open an issue first** to discuss the change. This prevents duplicated effort and lets us talk through tradeoffs before code is written.
- For bugs, small documentation fixes, and obvious improvements, a PR is fine without a prior issue.

## Development setup

See the [Quick start](README.md#quick-start-from-source) section of the README for installing dependencies and running the app. In short:

```bash
npm install
cd sidecar && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cd ..
npm run tauri dev
```

## Project layout

High-level map (see [ARCHITECTURE.md](ARCHITECTURE.md) for detail):

- `src/` — React + TypeScript frontend
- `src-tauri/` — Rust Tauri shell
- `sidecar/` — Python FastAPI / Whisper sidecar
- `scripts/` — Build and ad-hoc test scripts
- `dictate/` — Legacy Python CLI (separate from the desktop app)

## Making changes

1. Fork and branch from `main`.
2. Keep changes focused — one logical change per PR. Smaller PRs get reviewed faster.
3. Run the type checks and formatters before opening a PR:
   - Frontend: `npx tsc --noEmit`
   - Rust: `cd src-tauri && cargo check && cargo fmt`
4. **Test manually.** There is no automated test suite yet. Before submitting a PR, exercise the code path you changed end-to-end:
   - Launch the app (`npm run tauri dev`).
   - Verify the affected screen renders, the hotkey still works, and a transcription round-trips through the sidecar.
   - For Wayland-specific code, test on both X11 and Wayland if you can.
5. Describe the change in the PR: what and why. A screenshot helps for UI changes.

## Ad-hoc sidecar testing

The `scripts/` folder contains standalone Python scripts for exercising the sidecar without the Tauri shell:

- `test_recorder.py` — microphone capture round-trip
- `test_transcriber.py` — transcription on a fixed audio file
- `test_record_and_transcribe.py` — end-to-end record → transcribe
- `test_hotkey_record.py` — hotkey integration

Run them from inside the sidecar venv.

## Coding notes

- **No feature creep in bug fixes.** A bug fix PR should fix that bug. Refactors go in their own PR.
- **Keep comments to a minimum.** Explain *why* for non-obvious decisions; don't narrate *what* the code does.
- **No trailing summaries in commit messages.** Describe the change concisely.

## Licensing

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
