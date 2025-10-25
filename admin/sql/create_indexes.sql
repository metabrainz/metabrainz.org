BEGIN;

-- TODO: Add some, if needed.

CREATE INDEX moderation_log_user_id_idx ON moderation_log (user_id);

CREATE INDEX idx_webhook_delivery_status ON webhook_delivery(status);
CREATE INDEX idx_webhook_delivery_retry ON webhook_delivery(next_retry_at) WHERE status IN ('pending', 'failed');
CREATE INDEX idx_webhook_events ON webhook USING GIN(events);

COMMIT;
