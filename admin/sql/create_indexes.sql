BEGIN;

CREATE INDEX payment_supporter_id_idx ON payment (supporter_id);

CREATE UNIQUE INDEX user_login_id_idx ON "user" (login_id);
CREATE UNIQUE INDEX user_name_unq_idx ON "user" (LOWER(name));
-- not unique: an address may legitimately be shared between accounts. These back
-- the case insensitive duplicate lookups, which a plain btree cannot serve.
CREATE INDEX user_email_idx ON "user" (LOWER(email));
CREATE INDEX user_unconfirmed_email_idx ON "user" (LOWER(unconfirmed_email));
CREATE INDEX old_username_username_idx ON old_username (LOWER(username));
CREATE INDEX moderation_log_user_id_idx ON moderation_log (user_id);

CREATE INDEX idx_webhook_delivery_status ON webhook_delivery(status);
CREATE INDEX idx_webhook_delivery_retry ON webhook_delivery(next_retry_at) WHERE status IN ('pending', 'failed');
CREATE INDEX idx_webhook_events ON webhook USING GIN(events);

COMMIT;
