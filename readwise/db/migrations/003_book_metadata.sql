-- Add extended Calibre metadata fields to books
ALTER TABLE books ADD COLUMN publisher    TEXT NOT NULL DEFAULT '';
ALTER TABLE books ADD COLUMN series       TEXT NOT NULL DEFAULT '';
ALTER TABLE books ADD COLUMN series_index REAL NOT NULL DEFAULT 0;
ALTER TABLE books ADD COLUMN description  TEXT NOT NULL DEFAULT '';
ALTER TABLE books ADD COLUMN tags         TEXT NOT NULL DEFAULT '[]'; -- JSON list of strings
ALTER TABLE books ADD COLUMN rating       REAL NOT NULL DEFAULT 0;    -- 0–10 (Calibre scale)
ALTER TABLE books ADD COLUMN pub_date     TEXT NOT NULL DEFAULT '';   -- ISO date or year string
ALTER TABLE books ADD COLUMN language     TEXT NOT NULL DEFAULT '';
