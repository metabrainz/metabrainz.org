CREATE TYPE webhook_delivery_status_type AS ENUM ('pending', 'processing', 'delivered', 'failed');

BEGIN;

CREATE TABLE webhook (
    id                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name               TEXT NOT NULL,
    url                TEXT NOT NULL,
    secret             TEXT NOT NULL,
    events             TEXT[] NOT NULL,
    is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE webhook_delivery (
    id                 UUID NOT NULL PRIMARY KEY,
    webhook_id         INTEGER NOT NULL,
    event_type         TEXT NOT NULL,
    payload            JSONB NOT NULL,
    status             webhook_delivery_status_type NOT NULL,
    response_status    INTEGER,
    response_headers   JSONB,
    response_body      TEXT,
    error_message      TEXT,
    retry_count        INTEGER NOT NULL DEFAULT 0,
    next_retry_at      TIMESTAMP WITH TIME ZONE,
    created_at         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE webhook_delivery ADD CONSTRAINT webhook_delivery_webhook_fk FOREIGN KEY (webhook_id) REFERENCES webhook(id) ON DELETE CASCADE;

CREATE INDEX idx_webhook_delivery_status ON webhook_delivery(status);
CREATE INDEX idx_webhook_delivery_retry ON webhook_delivery(next_retry_at) WHERE status IN ('pending', 'failed');
CREATE INDEX idx_webhook_events ON webhook USING GIN(events);

COMMIT;
