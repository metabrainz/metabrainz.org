from datetime import datetime, timedelta, timezone
from typing import Any

from celery import shared_task
from flask import current_app
from sqlalchemy import text

from metabrainz.model import db


DELETE_OLD_TOKENS_SQL = """
DELETE FROM oauth.{table_name}
WHERE
    (
        COALESCE(revoked, FALSE) = TRUE
        AND issued_at IS NOT NULL
        AND issued_at < :cutoff_date
    )
    OR (
        issued_at IS NOT NULL
        AND expires_in IS NOT NULL
        AND issued_at + (expires_in * INTERVAL '1 second') < :cutoff_date
    )
"""


@shared_task(name="metabrainz.oauth.tasks.cleanup_old_tokens")
def cleanup_old_tokens(days: int = 7) -> dict[str, Any]:
    """
    Delete expired or revoked OAuth tokens older than the retention window.

    Revoked tokens do not currently store a revocation timestamp, so their
    age is based on issued_at. Expired tokens are deleted only when the
    computed expiry timestamp is older than the retention window.
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        access_token_result = db.session.execute(
            text(DELETE_OLD_TOKENS_SQL.format(table_name="access_token")),
            {"cutoff_date": cutoff_date},
        )
        refresh_token_result = db.session.execute(
            text(DELETE_OLD_TOKENS_SQL.format(table_name="refresh_token")),
            {"cutoff_date": cutoff_date},
        )
        db.session.commit()

        deleted_access_tokens = access_token_result.rowcount or 0
        deleted_refresh_tokens = refresh_token_result.rowcount or 0
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
            "access_tokens": 0,
            "refresh_tokens": 0,
            "total": 0,
            "error": str(e),
        }
