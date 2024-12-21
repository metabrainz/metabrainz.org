BEGIN;

ALTER TABLE supporter ADD COLUMN user_id INTEGER;
UPDATE supporter SET user_id = musicbrainz_row_id;

ALTER TABLE supporter ADD CONSTRAINT supporter_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES "user" (id)
    ON UPDATE CASCADE ON DELETE SET NULL;

COMMIT;
