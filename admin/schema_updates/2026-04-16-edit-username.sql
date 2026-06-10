ALTER TYPE moderation_action_type ADD VALUE 'delete';
ALTER TYPE moderation_action_type ADD VALUE 'edit_username';

BEGIN;

CREATE TABLE old_username (
    id          INTEGER GENERATED ALWAYS AS IDENTITY,
    username    TEXT NOT NULL,
    deleted_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE old_username ADD CONSTRAINT old_username_pkey PRIMARY KEY (id);
CREATE INDEX old_username_username_idx ON old_username (username);

COMMIT;
