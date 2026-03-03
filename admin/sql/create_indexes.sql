BEGIN;

CREATE INDEX payment_supporter_id_idx ON payment (supporter_id);

CREATE INDEX moderation_log_user_id_idx ON moderation_log (user_id);

COMMIT;
