-- Migration 001: cover art + read-progress tracking
-- Additive and non-breaking: both columns are nullable, so the previously
-- deployed code (which never references them) keeps working unchanged.

BEGIN;

-- Cover image URL scraped from MangaPill (nullable; falls back to a
-- generated placeholder in the UI when absent).
ALTER TABLE manga ADD COLUMN IF NOT EXISTS cover_url TEXT;

-- URL of the most recent chapter the user has read. Drives the "unread"
-- count and the "Continue" target.
ALTER TABLE manga ADD COLUMN IF NOT EXISTS last_read_url TEXT;

-- Backfill: mark every existing series as caught-up (last_read = newest
-- chapter), so the new read-tracking does not flood the user with "unread"
-- alerts for chapters they have presumably already read.
UPDATE manga
SET last_read_url = (
    SELECT url FROM chapters
    WHERE chapters.manga_id = manga.id
    ORDER BY url DESC
    LIMIT 1
)
WHERE last_read_url IS NULL;

COMMIT;
