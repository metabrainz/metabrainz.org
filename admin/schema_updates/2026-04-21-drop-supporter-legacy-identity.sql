BEGIN;

ALTER TABLE supporter DROP COLUMN musicbrainz_id;
ALTER TABLE supporter DROP COLUMN musicbrainz_row_id;
ALTER TABLE supporter DROP COLUMN contact_email;

COMMIT;
