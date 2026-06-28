-- Migration 002: store cover images in the database
-- The MangaPill CDN enforces hotlink protection, so the browser cannot load
-- covers directly. We download each cover once (server-side, with the right
-- Referer) and keep the bytes here; the /cover endpoint serves them.

BEGIN;

-- Raw image bytes (not base64 — bytea avoids the ~33% encoding overhead).
ALTER TABLE manga ADD COLUMN IF NOT EXISTS cover_image BYTEA;

-- Content-Type to serve the bytes with (e.g. image/jpeg, image/png).
ALTER TABLE manga ADD COLUMN IF NOT EXISTS cover_mime TEXT;

COMMIT;
