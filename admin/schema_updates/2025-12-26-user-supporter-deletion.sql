BEGIN;

ALTER TABLE supporter DROP CONSTRAINT supporter_user_id_fkey;
ALTER TABLE supporter ADD CONSTRAINT supporter_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES "user" (id)
    ON UPDATE CASCADE ON DELETE RESTRICT;

COMMIT;

ALTER TYPE moderation_action_type ADD VALUE 'delete';
