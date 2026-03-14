# ReadWise Desktop — Product Specification

## Overview
A Python/PySide6 desktop reading application built around focus and consistent daily habits. Breaks books into manageable daily chunks, tracks progress with gamification, and exports highlights/notes to Obsidian.

---

## Core Principles
- **Friction-free reading** — open a book and read, minimal setup required
- **Chunked progress** — never stare at a whole book; only see today's reading
- **Rewarding consistency** — streaks, badges, and visible progress create motivation
- **Capture without interruption** — highlight and note without breaking flow
- **Obsidian-first export** — your annotations live in your PKM, not locked in the app

---

## Platforms
- Windows, macOS, Linux (via PySide6)
- Local-only, offline-first
- Calibre library integration via filesystem (no Calibre running required)
- All book metadata sourced from Calibre's `metadata.opf` (title, author, tags, series, cover)
- One book record per Calibre folder — multiple format files (epub/pdf/mobi) consolidated into one entry

---

## Screens / Views

### 1. Library View
- Reads Calibre library folder structure
- Displays books as cards: cover art, title, author, series ("X of N"), progress, status badge
- **Card click interactions:**
  - Title → open reader
  - Author → filter library to that author
  - Series label → series drill-down view
  - Status badge → open reader; Shift+click → confirm reset progress
- **Sort bar:** Title / Author / Series / Pub Date; clicking active sort toggles ↑/↓ direction; direction is modal (persists when switching sort key)
- **Search bar:** plain text searches titles; prefixes `author:`, `series:`, `tag:`, `publisher:` search those fields
- **View toggle:** All Books / By Series (groups cards by series)
- **Filter:** Currently Reading (active sessions)
- **Library button** always resets all filters, search, and drill-down state
- **Series "X of N":** X = book's `series_index`; N = count of whole-numbered indices in series (excludes .5 novellas)
- **Card progress style** (user setting): progress bar only / bar + % / % only
- **Dynamic grid:** columns reflow as window is resized
- "Add book" — point to any epub/pdf/mobi file outside Calibre (planned)

### 2. Book Setup / Onboarding (first open of a book)
- Auto-detects chapters, sections, page count
- User selects chunking strategy:
  - **By pages** — set daily page target
  - **By chapters** — one or more chapters per day
  - **By sections** — for books with sub-chapter divisions (pericopes, sections)
  - **By time** — estimated reading time per session (app estimates WPM)
- User sets a daily reading goal (time of day reminder optional)
- Preview of the generated schedule (start → end date)

### 3. Reader View
- **Two modes (toggle):**
  - **Chunk mode** — shows only today's assigned reading, nothing else visible
  - **Full mode** — full book with current chunk highlighted/marked (planned)
- EPUB rendered as extracted HTML in a QWebEngineView panel (via ebooklib + file:// URLs)
- PDF renderer — planned Phase 3
- Navigation: prev/next session/chapter buttons; page/location indicator
- **Keyboard nav:** Left/Right arrows → previous/next session or chapter; Up/Down → scroll the reading pane
- **Scroll position restore:** session ended mid-chunk resumes at the exact scroll position
- Font size, font family, line spacing controls (persisted per book) — planned
- Dark/light/sepia themes — planned

### 4. Highlight & Note Panel
- Select text → color picker appears (user-defined color tags)
- Click highlight → inline note field appears (optional)
- Side panel (collapsible) shows all highlights for current chunk/chapter
- Tags shown as colored pills with user-defined label (e.g., #important, #question)

### 5. Progress & Stats View
- Current streak (days in a row)
- Longest streak
- Books completed
- Pages/words read this week/month/all time
- Per-book progress timeline
- Badges earned (displayed as a shelf/wall)

### 6. Session Summary (shown on session close)
- What you read today (chunk title, pages)
- Highlights + notes captured this session
- Streak status (maintained / new record / broken)
- "Sync to Obsidian" confirmation (auto-fires, shows result)
- Badge unlock notification if applicable

### 7. Settings
- Calibre library path
- Obsidian vault path
- **Card progress style:** progress bar only / bar + percentage / percentage only
- Color tag definitions (name + color) — planned Phase 2
- Default chunking strategy
- Reading speed calibration (WPM) — planned
- Notification/reminder preferences — planned
- Theme — planned

---

## Data Model

### Book
```
id                  UUID
calibre_id          str (from Calibre metadata.opf — used as dedup key)
title               str
author              str
cover_path          str
available_formats   JSON list: [{format: "EPUB", path: "..."}, ...]
active_format       enum: EPUB | PDF | MOBI (user-selected, default: epub > pdf > mobi)
total_pages         int
total_words         int (estimated)
total_chapters      int
added_date          date
status              enum: NOT_STARTED | IN_PROGRESS | COMPLETE
```

**Format deduplication rule:** One Calibre book folder = one Book record, regardless of how
many format files (epub/pdf/mobi) exist inside it. The scanner keys on the Calibre book folder,
not on individual files. All available formats are stored in `available_formats`; the user can
switch active format per book in settings.

### ReadingPlan
```
id                  UUID
book_id             FK → Book
chunk_strategy      enum: PAGES | CHAPTERS | SECTIONS | TIME
chunk_size          int (pages, chapter count, section count, or minutes)
start_date          date
target_end_date     date
daily_goal_time     time (optional reminder)
```

### Chunk
```
id                  UUID
plan_id             FK → ReadingPlan
sequence            int
label               str (e.g., "Chapter 3" or "Pages 45–67")
start_location      str (page number or epub CFI)
end_location        str
scheduled_date      date
completed_date      date | null
```

### ReadingSession
```
id                  UUID
book_id             FK → Book
chunk_id            FK → Chunk
started_at          datetime
ended_at            datetime
pages_read          int
words_read          int (estimated)
synced_to_obsidian  bool
```

### Highlight
```
id                  UUID
book_id             FK → Book
session_id          FK → ReadingSession
passage             str (the selected text)
location            str (page or epub CFI)
chapter_label       str
color_tag_id        FK → ColorTag
created_at          datetime
```

### Note
```
id                  UUID
highlight_id        FK → Highlight
body                str
created_at          datetime
updated_at          datetime
```

### ColorTag
```
id                  UUID
name                str (e.g., "Important")
color_hex           str (e.g., "#FFD700")
obsidian_tag        str (e.g., "#important")
```

### UserStats
```
id                  UUID
current_streak      int
longest_streak      int
last_read_date      date
total_books_complete int
total_pages_read    int
total_words_read    int
badges              JSON list of badge IDs
```

---

## Gamification

### Streaks
- Streak increments if user completes at least one chunk per calendar day
- Grace period: one missed day allowed per 7-day streak (configurable)
- Streak freeze: earnable badge perk

### Badges (initial set)
| Badge | Trigger |
|---|---|
| First Page | Complete first reading session |
| On a Roll | 3-day streak |
| Week Warrior | 7-day streak |
| Bookworm | 30-day streak |
| Chapter Champ | Complete 10 chapters total |
| Speed Reader | Read 10,000 words in one session |
| Annotator | Create 50 highlights |
| Finisher | Complete first book |
| Librarian | Complete 5 books |
| Deep Thinker | Write 20 notes |

---

## Obsidian Integration

### Output: One markdown note per book
- File: `{Vault}/Reading/{Author} - {Title}.md`
- Written on session end (auto-sync)
- Manual "Sync Now" button in settings

### Note format
```markdown
---
title: "The Book Title"
author: "Author Name"
status: in-progress
started: 2026-03-01
format: epub
tags: [reading, books]
---

# The Book Title

## Chapter 3 — The Call

> "The highlighted passage text goes here."
#important · p. 42
Note: The user's note attached to this highlight.

---

> "Another highlighted passage."
#question · p. 45
```

### Sync behavior
- App appends new highlights/notes since last sync
- Does not overwrite or delete existing content
- Obsidian is append-only from the app's perspective
- One-way: app → Obsidian

---

## File Format Support

| Format | Reading | Highlight | Notes |
|---|---|---|---|
| EPUB | Full render | Yes | Yes |
| PDF | Full render | Yes (text layer) | Yes |
| MOBI | Convert via calibredb or kindleunpack | Yes | Yes |

---

## Out of Scope (v1)
- Notion integration (planned v2)
- Cloud sync / multi-device
- Social/sharing features
- TTS / read-aloud
- Bidirectional Obsidian sync
- Mobile app
