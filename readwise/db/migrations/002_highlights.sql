-- Color tags: user-defined highlight categories
CREATE TABLE IF NOT EXISTS color_tags (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,              -- e.g. "Important"
    color_hex       TEXT NOT NULL,              -- e.g. "#FFD700"
    obsidian_tag    TEXT NOT NULL               -- e.g. "#important"
);

-- Seed default color tags
INSERT OR IGNORE INTO color_tags (id, name, color_hex, obsidian_tag) VALUES
    ('tag-yellow',  'Important',  '#FFD700', '#important'),
    ('tag-red',     'Question',   '#FF6B6B', '#question'),
    ('tag-green',   'Action',     '#51CF66', '#action'),
    ('tag-blue',    'Reference',  '#74C0FC', '#reference');

-- Highlights: a selected passage with a color tag
CREATE TABLE IF NOT EXISTS highlights (
    id              TEXT PRIMARY KEY,
    book_id         TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    session_id      TEXT REFERENCES reading_sessions(id) ON DELETE SET NULL,
    passage         TEXT NOT NULL,              -- the selected text
    location        TEXT NOT NULL,              -- page number or epub CFI
    chapter_label   TEXT NOT NULL DEFAULT '',
    color_tag_id    TEXT NOT NULL REFERENCES color_tags(id),
    created_at      TEXT NOT NULL               -- ISO datetime
);

-- Notes: one optional note per highlight
CREATE TABLE IF NOT EXISTS notes (
    id              TEXT PRIMARY KEY,
    highlight_id    TEXT NOT NULL REFERENCES highlights(id) ON DELETE CASCADE,
    body            TEXT NOT NULL,
    created_at      TEXT NOT NULL,              -- ISO datetime
    updated_at      TEXT NOT NULL               -- ISO datetime
);
