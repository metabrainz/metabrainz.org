ALTER TYPE moderation_action_type ADD VALUE 'delete';
ALTER TYPE moderation_action_type ADD VALUE 'edit_username';

BEGIN;

CREATE TABLE old_username (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username    TEXT NOT NULL,
    deleted_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX old_username_username_idx ON old_username (username);
CREATE UNIQUE INDEX user_name_unq_idx ON "user" (name);

COMMIT;
