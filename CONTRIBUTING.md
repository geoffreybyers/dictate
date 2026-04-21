# Contributing

## Dev environment

```bash
python3 -m venv .venv
.venv/bin/pip install -e .[dev]
```

## Run the daemon

```bash
.venv/bin/private-dictate
```

## Tests

```bash
.venv/bin/pytest
```

TDD expected: add a failing test, implement, commit.

## Style

- Small, focused modules. One clear responsibility per file.
- Typed exceptions live in `private_dictate/errors.py`.
- Don't mock the daemon; mock the hardware (`Transcriber`, `Recorder`, `HotkeyListener`).
- Keep TUI screens free of I/O — read through `private_dictate.paths` helpers.

## Commits

Conventional commit prefixes: `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `ci:`. Include scope in parens where useful (`feat(tui): ...`).

## Opening a PR

- Ensure `pytest` is green locally.
- Update `README.md` / `ARCHITECTURE.md` if behavior or module layout changes.
