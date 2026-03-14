-- Books: one record per Calibre folder, all formats consolidated
CREATE TABLE IF NOT EXISTS books (
    id              TEXT PRIMARY KEY,
    calibre_id      TEXT UNIQUE,                -- Calibre book folder name, dedup key
    title           TEXT NOT NULL,
    author          TEXT NOT NULL DEFAULT '',
    cover_path      TEXT NOT NULL DEFAULT '',
    available_formats TEXT NOT NULL DEFAULT '[]', -- JSON: [{format, path}, ...]
    active_format   TEXT NOT NULL DEFAULT 'EPUB', -- EPUB | PDF | MOBI
    total_pages     INTEGER NOT NULL DEFAULT 0,
    total_words     INTEGER NOT NULL DEFAULT 0,
    total_chapters  INTEGER NOT NULL DEFAULT 0,
    added_date      TEXT NOT NULL,              -- ISO date
    status          TEXT NOT NULL DEFAULT 'NOT_STARTED' -- NOT_STARTED | IN_PROGRESS | COMPLETE
);

-- Reading plans: one per book (replace if user re-plans)
CREATE TABLE IF NOT EXISTS reading_plans (
    id              TEXT PRIMARY KEY,
    book_id         TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chunk_strategy  TEXT NOT NULL,              -- PAGES | CHAPTERS | SECTIONS | TIME
    chunk_size      INTEGER NOT NULL,           -- pages, chapter count, section count, or minutes
    start_date      TEXT NOT NULL,              -- ISO date
    target_end_date TEXT NOT NULL,              -- ISO date
    daily_goal_time TEXT,                       -- HH:MM, optional reminder time
    created_at      TEXT NOT NULL
);

-- Chunks: individual reading units generated from a plan
CREATE TABLE IF NOT EXISTS chunks (
    id              TEXT PRIMARY KEY,
    plan_id         TEXT NOT NULL REFERENCES reading_plans(id) ON DELETE CASCADE,
    book_id         TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    sequence        INTEGER NOT NULL,
    label           TEXT NOT NULL,              -- e.g. "Chapter 3" or "Pages 45–67"
    start_location  TEXT NOT NULL,              -- page number or epub CFI
    end_location    TEXT NOT NULL,
    scheduled_date  TEXT NOT NULL,              -- ISO date
    completed_date  TEXT                        -- ISO date, null if not done
);

-- Reading sessions
CREATE TABLE IF NOT EXISTS reading_sessions (
    id                  TEXT PRIMARY KEY,
    book_id             TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chunk_id            TEXT REFERENCES chunks(id) ON DELETE SET NULL,
    started_at          TEXT NOT NULL,          -- ISO datetime
    ended_at            TEXT,                   -- ISO datetime, null if in progress
    pages_read          INTEGER NOT NULL DEFAULT 0,
    words_read          INTEGER NOT NULL DEFAULT 0,
    synced_to_obsidian  INTEGER NOT NULL DEFAULT 0  -- boolean
);

-- User stats: single-row table
CREATE TABLE IF NOT EXISTS user_stats (
    id                  TEXT PRIMARY KEY DEFAULT 'singleton',
    current_streak      INTEGER NOT NULL DEFAULT 0,
    longest_streak      INTEGER NOT NULL DEFAULT 0,
    last_read_date      TEXT,                   -- ISO date
    total_books_complete INTEGER NOT NULL DEFAULT 0,
    total_pages_read    INTEGER NOT NULL DEFAULT 0,
    total_words_read    INTEGER NOT NULL DEFAULT 0,
    badges              TEXT NOT NULL DEFAULT '[]' -- JSON list of badge IDs
);

-- Seed the single user_stats row
INSERT OR IGNORE INTO user_stats (id) VALUES ('singleton');
