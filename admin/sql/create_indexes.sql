BEGIN;

CREATE INDEX payment_supporter_id_idx ON payment (supporter_id);

CREATE UNIQUE INDEX user_login_id_idx ON "user" (login_id);
CREATE UNIQUE INDEX user_name_unq_idx ON "user" (name);
CREATE INDEX old_username_username_idx ON old_username (username);
CREATE INDEX moderation_log_user_id_idx ON moderation_log (user_id);

CREATE INDEX idx_webhook_delivery_status ON webhook_delivery(status);
CREATE INDEX idx_webhook_delivery_retry ON webhook_delivery(next_retry_at) WHERE status IN ('pending', 'failed');
CREATE INDEX idx_webhook_events ON webhook USING GIN(events);

COMMIT;
