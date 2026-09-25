BEGIN;

CREATE TABLE crm_sync (
    supporter_id INTEGER PRIMARY KEY REFERENCES supporter (id) ON DELETE CASCADE,
    pending BOOLEAN NOT NULL DEFAULT TRUE,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    synced_at TIMESTAMPTZ,
    person_id UUID,
    company_id UUID
);
CREATE INDEX crm_sync_pending_idx ON crm_sync (next_attempt_at) WHERE pending;

COMMIT;
