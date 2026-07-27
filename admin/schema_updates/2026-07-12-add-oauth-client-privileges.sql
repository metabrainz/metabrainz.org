BEGIN;

ALTER TABLE oauth.client
    ADD COLUMN privileges INTEGER NOT NULL DEFAULT 0
        CONSTRAINT client_privileges_non_negative CHECK (privileges >= 0);

COMMIT;
