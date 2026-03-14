# ReadWise Desktop — Context

## What we're building
A Python/PySide6 desktop reading application built around focus and consistent daily habits. Breaks books into manageable daily chunks, tracks progress with streaks and gamification, and exports highlights/notes to Obsidian.

## Stack
- **GUI:** Python + PySide6 (Qt6)
- **Database:** SQLite (app-managed, separate from Calibre)
- **Book rendering:** ebooklib extracts EPUB chapters to a temp cache dir; `QWebEngineView` loads them via `file://` URLs. No epub.js or pdf.js used.
- **Library source:** Calibre filesystem integration — reads `metadata.opf` and `cover.jpg` per book folder. No Calibre process required, no writes to Calibre's database.
- **Integrations:** Obsidian (Phase 2); Notion (Phase 4, not started)

## Current Status
Phase 1 (MVP) is functionally complete:
- App boots, scans Calibre library, displays book cards
- Book setup wizard (chunking strategy, schedule preview)
- EPUB reader with `QWebEngineView`, session start/end, progress tracking
- Streak counter, basic stats

Library UI is substantially enhanced beyond the original spec:
- Book card click interactions (title → read, author → filter, series → drill-down, status badge → read / shift+click reset)
- Sort bar with ascending/descending toggle (modal direction)
- Search bar with prefix support (`author:`, `series:`, `tag:`, `publisher:`)
- Dynamic grid column reflow on window resize
- Card progress style setting (bar / bar+% / % only)
- Scroll position restore within a session

## Next Step
Phase 2: highlights, notes, and Obsidian sync.
