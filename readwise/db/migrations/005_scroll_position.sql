-- Remember scroll position within the current chunk/session
ALTER TABLE reading_plans ADD COLUMN last_scroll_pct INTEGER NOT NULL DEFAULT 0;
