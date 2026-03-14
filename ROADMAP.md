# ReadWise Desktop — Phased Roadmap

---

## Phase 1 — MVP: Read & Track
**Goal:** Open a book, set a reading plan, read daily chunks, track progress.
No frills. Just the core reading loop working end to end.

### Deliverables
- [x] Project scaffold (PySide6, SQLite, folder structure)
- [x] Calibre library scanner (reads metadata.opf, cover.jpg, finds epub/pdf files)
- [x] Book model + SQLite schema (Books, ReadingPlans, Chunks, Sessions)
- [x] Library view — book cards with cover, title, author, series, progress bar
- [x] Book setup wizard — choose chunking strategy, set daily goal, preview schedule
- [x] Chunk generator — produces Chunk records from plan settings
- [x] EPUB renderer (QWebEngineView + ebooklib → extracted HTML via file:// URLs)
- [ ] PDF renderer — planned Phase 3
- [x] Reader view — chunk/session navigation, keyboard nav (←→ prev/next, ↑↓ scroll)
- [x] Session tracking (start/end time, progress %)
- [x] Scroll position restore (resume mid-session at exact scroll position)
- [x] Basic progress stats (% complete per book)
- [x] Streak counter (simple, no grace period yet)
- [ ] Session summary screen — partial

### Also completed (beyond original scope)
- [x] Sort bar with ascending/descending direction toggle
- [x] Search bar with prefix support (author:, series:, tag:, publisher:)
- [x] Author filter, series drill-down, By Series view
- [x] Library button always resets all filter/search/drill-down state
- [x] Card progress style setting (bar / bar+% / % only)
- [x] Dynamic grid column reflow on window resize
- [x] Series "X of N" (N = whole-numbered books only)

### Success criteria
User can open a Calibre library, pick a book, set up a plan, and read their daily chunk with progress tracked.

---

## Phase 2 — Highlights, Notes & Obsidian
**Goal:** Capture annotations during reading and export to Obsidian.

### Deliverables
- [ ] Color tag system (ColorTag model, settings UI to define tags)
- [ ] Text selection → highlight in epub renderer
- [ ] Text selection → highlight in PDF renderer
- [ ] Inline note attachment to highlight
- [ ] Highlight side panel (collapsible, shows current chunk/chapter annotations)
- [ ] Highlight persistence (SQLite)
- [ ] Obsidian sync engine (append-only markdown writer)
- [ ] Auto-sync on session end
- [ ] Manual "Sync Now" in settings
- [ ] Session summary updated to show highlights captured + sync status

### Success criteria
User highlights a passage, adds a note, closes the session, and finds a formatted markdown note in their Obsidian vault.

---

## Phase 3 — Gamification & Reader Polish
**Goal:** Make consistency rewarding. Polish the reading experience.

### Deliverables
- [ ] Badge system (data model + unlock logic for initial badge set)
- [ ] Badge unlock notification (end of session)
- [ ] Progress & stats view (streaks, badges shelf, reading history)
- [ ] Streak grace period (configurable)
- [ ] Full mode in reader (whole book visible, chunk highlighted)
- [ ] Reader themes (light / dark / sepia)
- [ ] Font controls (size, family, line spacing) persisted per book
- [ ] MOBI support (conversion pipeline via kindleunpack or calibredb)
- [ ] Reminder/notification system (daily reading reminder at set time)

### Success criteria
User has a visible streak, earns badges, and the reading experience feels polished enough for daily use.

---

## Phase 4 — Extended Integrations & Library Features
**Goal:** Notion integration, library management improvements, power-user features.

### Deliverables
- [ ] Notion integration (highlights/notes → Notion database)
- [ ] Books outside Calibre (add any epub/pdf/mobi by file path)
- [ ] Reading speed calibration (WPM test, auto-adjust time estimates)
- [ ] Search across highlights/notes (in-app)
- [ ] Export highlights to other formats (CSV, plain markdown)
- [ ] Section-level chunking for books with pericopes/subsections
- [ ] Per-book reading statistics (pace chart, session history)

### Success criteria
Notion sync works. User can manage a reading list outside Calibre. Power features don't get in the way of daily reading.

---

## Phase 5 — Future / Nice-to-Have
*No commitment — revisit after Phase 4*
- Cloud backup of progress/highlights (optional, user-controlled)
- Multi-device sync
- TTS / read-aloud mode
- Bidirectional Obsidian sync
- Reading groups / shared highlights
- Mobile companion app
