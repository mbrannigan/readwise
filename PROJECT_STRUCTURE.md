# ReadWise Desktop — Project Structure

```
readwise/
├── main.py                         # Entry point — launches PySide6 QApplication
│
├── config/
│   └── settings.py                 # User settings (vault path, library path, defaults)
│                                   # Persisted as JSON in platform app data dir
│
├── db/
│   ├── database.py                 # SQLite connection, auto-migrations runner
│   ├── migrations/
│   │   ├── 001_initial.sql         # Books, ReadingPlans, Chunks, Sessions
│   │   ├── 002_highlights.sql      # Highlights, Notes, ColorTags (schema only)
│   │   ├── 003_book_metadata.sql   # Extended book metadata fields
│   │   ├── 004_last_position.sql   # last_chunk_index on reading_plans
│   │   └── 005_scroll_position.sql # last_scroll_pct on reading_plans
│   └── models/
│       ├── book.py                 # Book dataclass + DB queries
│       ├── reading_plan.py         # ReadingPlan + Chunk dataclasses + queries
│       │                           # includes get/save last_scroll_pct
│       ├── session.py              # ReadingSession dataclass + queries
│       └── stats.py                # UserStats dataclass + queries
│
├── core/
│   ├── calibre_scanner.py          # Reads Calibre library folder, parses metadata.opf
│   ├── chunk_generator.py          # Generates Chunk records from a ReadingPlan
│   ├── session_manager.py          # Starts/ends sessions, updates stats
│   └── streak_engine.py            # Streak calculation + grace period logic
│
├── readers/
│   ├── base_reader.py              # Abstract base: load(), get_chapter_list(), get_toc()
│   └── epub_reader.py              # ebooklib-based EPUB parser
│                                   # Extracts chapters to cache dir; ReaderPanel loads via file://
│                                   # pdf_reader.py and mobi_reader.py — planned Phase 3
│
├── integrations/
│   ├── obsidian/                   # Phase 2 — append-only markdown writer (not yet implemented)
│   │   └── __init__.py
│   └── notion/                     # Phase 4 — placeholder only
│       └── __init__.py
│
├── ui/
│   ├── main_window.py              # QMainWindow, nav sidebar, view switcher
│   ├── views/
│   │   ├── library_view.py         # Book card grid, sort/filter/search bar, series drill-down
│   │   ├── reader_view.py          # Reading area, session controls, keyboard nav
│   │   ├── stats_view.py           # Streaks, badges shelf, reading history
│   │   └── settings_view.py        # Settings form (library path, vault path, card style, etc.)
│   ├── dialogs/
│   │   ├── book_detail_dialog.py   # Book info dialog (pre-setup)
│   │   └── book_setup_dialog.py    # Chunking strategy wizard (first open of a book)
│   └── widgets/
│       ├── book_card.py            # Individual book card (cover, title, author, series, progress)
│       ├── reader_panel.py         # QWebEngineView-based book renderer + scroll control
│       └── series_card.py          # Series group card for By Series view
│
├── assets/
│   └── icons/                      # App icons
│
└── tests/
    └── __init__.py
```

---

## Key Dependency List

| Package | Purpose |
|---|---|
| `PySide6` | GUI framework (Qt6 for Python) |
| `PySide6-WebEngine` | QWebEngineView for EPUB rendering |
| `ebooklib` | EPUB parsing and chapter extraction |
| `lxml` | XML/HTML parsing (Calibre metadata.opf) |
| `Pillow` | Cover image processing |

---

## Data Storage

| What | Where |
|---|---|
| App database | `{platform_appdata}/readwise/readwise.db` (SQLite) |
| User settings | `{platform_appdata}/readwise/settings.json` |
| EPUB cache | `{platform_appdata}/readwise/epub_cache/` (extracted chapter HTML) |
| Obsidian output | `{user's vault path}/Reading/{Author} - {Title}.md` |

---

## Architecture Notes

**EPUB rendering:** ebooklib extracts chapter HTML to a temp cache directory. `ReaderPanel` (`QWebEngineView`) loads chapters via `file://` URLs. No epub.js or pdf.js — avoids JS dependency and works fully offline.

**Scroll restore:** `last_scroll_pct` stored on `reading_plans`. On book open, `ReaderPanel._restore_pct` is set before `_render()`; applied in `_on_load_finished` after the page fully loads.

**Calibre integration:** Read-only. Scanner reads `metadata.opf` and `cover.jpg` from each Calibre book folder. Never touches `metadata.db`.

**SQLite:** Local, zero-config. Migrations run automatically from `db/migrations/` on startup via `_migrations` tracking table.
