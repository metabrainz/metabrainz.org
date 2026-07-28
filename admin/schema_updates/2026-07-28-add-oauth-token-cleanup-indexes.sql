-- Run without a surrounding transaction so writes can continue while these
-- indexes are built.
CREATE INDEX CONCURRENTLY IF NOT EXISTS access_token_cleanup_idx
    ON oauth.access_token (issued_at, id)
    WHERE issued_at IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS refresh_token_cleanup_idx
    ON oauth.refresh_token (issued_at, id)
    WHERE issued_at IS NOT NULL;
