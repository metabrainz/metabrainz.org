BEGIN;

ALTER TABLE supporter ADD COLUMN musicbrainz_row_id INTEGER;
ALTER TABLE payment ADD COLUMN editor_id INTEGER;

COMMIT;
