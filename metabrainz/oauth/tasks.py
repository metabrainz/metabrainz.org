from datetime import datetime, timedelta, timezone
from typing import Any

from celery import shared_task
from flask import current_app
from sqlalchemy import Table, and_, delete, or_, select

from metabrainz.model import OAuth2AccessToken, OAuth2RefreshToken, db


TOKEN_CLEANUP_BATCH_SIZE = 5_000


def _cleanup_token_table(
    token_table: Table,
    cutoff_date: datetime,
    batch_size: int,
) -> int:
    deleted_total = 0
    expires_at = (
        token_table.c.issued_at
        + token_table.c.expires_in * timedelta(seconds=1)
    )
    candidates = (
        select(token_table.c.id)
        .where(
            token_table.c.issued_at.is_not(None),
            token_table.c.issued_at < cutoff_date,
            or_(
                token_table.c.revoked.is_(True),
                and_(
                    token_table.c.expires_in.is_not(None),
                    expires_at < cutoff_date,
                ),
            ),
        )
        .order_by(token_table.c.issued_at, token_table.c.id)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
        .cte("candidates")
    )
    statement = delete(token_table).where(
        token_table.c.id.in_(select(candidates.c.id))
    )

    while True:
        result = db.session.execute(statement)
        deleted = result.rowcount or 0
        db.session.commit()
        deleted_total += deleted

        if deleted < batch_size:
            return deleted_total


@shared_task(name="metabrainz.oauth.tasks.cleanup_old_tokens")
def cleanup_old_tokens(
    days: int = 7,
    batch_size: int = TOKEN_CLEANUP_BATCH_SIZE,
) -> dict[str, Any]:
    """
    Delete expired or revoked OAuth tokens older than the retention window.

    Tokens are deleted and committed in bounded batches. Locked rows are
    skipped and can be picked up by a later run.

    Revoked tokens do not currently store a revocation timestamp, so their
    age is based on issued_at. Expired tokens are deleted only when the
    computed expiry timestamp is older than the retention window.
    """
    deleted_access_tokens = 0
    deleted_refresh_tokens = 0

    try:
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        deleted_access_tokens = _cleanup_token_table(
            OAuth2AccessToken.__table__,
            cutoff_date,
            batch_size,
        )
        deleted_refresh_tokens = _cleanup_token_table(
            OAuth2RefreshToken.__table__,
            cutoff_date,
            batch_size,
        )

        result = {
            "access_tokens": deleted_access_tokens,
            "refresh_tokens": deleted_refresh_tokens,
            "total": deleted_access_tokens + deleted_refresh_tokens,
        }

        current_app.logger.info(
            f"Cleaned up OAuth tokens older than {days} days: {result}"
        )

        return result
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Error during OAuth token cleanup: {e}",
            exc_info=True,
        )
        return {
            "access_tokens": deleted_access_tokens,
            "refresh_tokens": deleted_refresh_tokens,
            "total": deleted_access_tokens + deleted_refresh_tokens,
            "error": str(e),
        }
