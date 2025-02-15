BEGIN;

-- TODO: Add some, if needed.

CREATE INDEX moderation_log_user_id_idx ON moderation_log (user_id);

COMMIT;
