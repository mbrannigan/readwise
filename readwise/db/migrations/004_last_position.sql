-- Remember last-viewed chunk index per reading plan
ALTER TABLE reading_plans ADD COLUMN last_chunk_index INTEGER NOT NULL DEFAULT 0;
