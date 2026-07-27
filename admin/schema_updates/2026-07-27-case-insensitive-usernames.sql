BEGIN;

DROP INDEX user_name_unq_idx;
CREATE UNIQUE INDEX user_name_unq_idx ON "user" (LOWER(name));

DROP INDEX old_username_username_idx;
CREATE INDEX old_username_username_idx ON old_username (LOWER(username));

COMMIT;
