BEGIN;

-- Now that user data lives in the MetaBrainz database (migrated from the MusicBrainz
-- editor table, where user.id == editor.id), wire up the foreign keys to "user"(id) that
-- were previously deferred because user data lived in the MusicBrainz database.
--
-- Prerequisite: the MusicBrainz editors must already be imported into the "user" table
-- (manage.py migrate_musicbrainz_users) so that these references resolve.

-- For nullable, best-effort references, drop any value that does not point at a migrated
-- user before adding the constraint.
UPDATE payment
   SET editor_id = NULL
 WHERE editor_id IS NOT NULL
   AND editor_id NOT IN (SELECT id FROM "user");

UPDATE oauth.access_token
   SET user_id = NULL
 WHERE user_id IS NOT NULL
   AND user_id NOT IN (SELECT id FROM "user");

-- NOT NULL references (oauth.client.owner_id, oauth.code.user_id,
-- oauth.refresh_token.user_id) cannot be nulled; if any of them point at a non-existent
-- user the ALTER below fails and the whole transaction rolls back, signalling that the
-- user migration is incomplete.

ALTER TABLE payment
    ADD CONSTRAINT payment_editor_id_fkey FOREIGN KEY (editor_id)
    REFERENCES "user" (id) MATCH SIMPLE
    ON UPDATE CASCADE ON DELETE SET NULL;

ALTER TABLE oauth.client
    ADD CONSTRAINT client_owner_id_fkey FOREIGN KEY (owner_id)
    REFERENCES "user" (id) ON DELETE CASCADE;

ALTER TABLE oauth.code
    ADD CONSTRAINT code_user_id_fkey FOREIGN KEY (user_id)
    REFERENCES "user" (id) ON DELETE CASCADE;

ALTER TABLE oauth.access_token
    ADD CONSTRAINT access_token_user_id_fkey FOREIGN KEY (user_id)
    REFERENCES "user" (id) ON DELETE CASCADE;

ALTER TABLE oauth.refresh_token
    ADD CONSTRAINT refresh_token_user_id_fkey FOREIGN KEY (user_id)
    REFERENCES "user" (id) ON DELETE CASCADE;

COMMIT;
