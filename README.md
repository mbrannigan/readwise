# ReadWise Desktop

A desktop reading app built around focus and consistency. Break books into manageable daily chunks, track your streak, and export highlights to Obsidian.

- Reads your existing [Calibre](https://calibre-ebook.com/) library — no migration needed
- EPUB rendering built-in (PDF planned)
- Chunked sessions: by chapter, pages, or time
- Streaks and progress tracking
- Highlights and notes → Obsidian (Phase 2)

---

## Requirements

- Python 3.11+
- A Calibre library folder (the app reads it; it never writes to it)
- Windows, macOS, or Linux

---

## Setup

```bash
# Clone the repo
git clone <repo-url>
cd readwise

# Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -e .
```

---

## Run

```bash
readwise
# or
python -m readwise.main
```

On first launch you will be prompted to point the app at your Calibre library folder.

---

## Project Layout

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for the full folder breakdown.

Key files:
- `readwise/main.py` — entry point
- `readwise/ui/main_window.py` — main window and navigation
- `readwise/db/database.py` — SQLite connection and migrations
- `readwise/config/settings.py` — user settings (library path, vault path, etc.)

---

## Data

| What | Where |
|---|---|
| App database | `%APPDATA%\readwise\readwise.db` (Windows) / `~/.local/share/readwise/` (Linux) / `~/Library/Application Support/readwise/` (macOS) |
| Settings | Same directory, `settings.json` |
| EPUB cache | Same directory, `epub_cache/` — safe to delete; rebuilt on next open |

The app **never modifies your Calibre library**. All app data is stored separately.

---

## Development

```bash
pip install -e ".[dev]"
pytest
```

> **Note on Windows:** PySide6 must be pinned to `6.8.2`. If you see
> `ImportError: DLL load failed while importing QtWidgets`, delete `.venv`
> and reinstall with `pip install "PySide6==6.8.2"`.

---

## About this project

This is a personal tool built for my own reading workflow — if you stumbled
across it and find it useful, great. Issues are welcome but I'm not actively
seeking contributions.

The codebase is built with AI assistance (Claude). Architecture, feature
decisions, and direction are all mine; Claude handles the implementation.

---

## Roadmap

See [ROADMAP.md](ROADMAP.md). Current status: Phase 1 complete (read + track). Phase 2 next (highlights + Obsidian).

## Spec

See [SPEC.md](SPEC.md) for the full feature specification.
