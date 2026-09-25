from datetime import datetime, timedelta, timezone
from uuid import UUID

from celery import shared_task
from flask import current_app

from metabrainz.crm.client import TwentyClient, CrmError
from metabrainz.crm.sync import sync_supporter
from metabrainz.model import db, Supporter
from metabrainz.model.crm_sync import CrmSync


def prepare_signup_sync(supporter):
    """Called before signup commits: no broker or HTTP operations here."""
    if current_app.config.get("CRM_ENABLED", False):
        db.session.flush()
        db.session.add(CrmSync(supporter_id=supporter.id))


def publish_signup_sync(supporter_id):
    """Called only after commit; the periodic scan recovers publication failures."""
    if not current_app.config.get("CRM_ENABLED", False):
        return
    try:
        sync_supporter_to_crm.apply_async(args=[supporter_id], retry=False)
    except Exception:
        # Avoid logging broker credentials or signup details from exception messages.
        current_app.logger.error("Could not queue CRM synchronization for supporter %s", supporter_id)


@shared_task(name="metabrainz.crm.tasks.sync_supporter_to_crm", soft_time_limit=90, time_limit=120, rate_limit="5/m")
def sync_supporter_to_crm(supporter_id):
    if not current_app.config.get("CRM_ENABLED", False):
        return
    client = None
    try:
        # Hold a row lock until the remote work is done. Duplicate deliveries skip
        # this row; a worker crash releases the lock and leaves durable pending work.
        mapping = CrmSync.query.filter_by(supporter_id=supporter_id, pending=True).with_for_update(
            skip_locked=True
        ).first()
        if mapping is None:
            db.session.rollback()
            return
        supporter = db.session.get(Supporter, supporter_id)
        client = TwentyClient(current_app.config)
        person_id, company_id = sync_supporter(client, supporter, mapping)
        mapping.person_id = UUID(person_id)
        mapping.company_id = UUID(company_id) if company_id else None
        mapping.pending = False
        mapping.last_error = None
        mapping.synced_at = datetime.now(timezone.utc)
        db.session.commit()
    except Exception as error:
        db.session.rollback()
        # Another worker may already have succeeded after our lock was released.
        mapping = CrmSync.query.filter_by(supporter_id=supporter_id, pending=True).with_for_update().first()
        if mapping is not None:
            mapping.attempts += 1
            mapping.last_error = str(error) if isinstance(error, CrmError) else type(error).__name__
            mapping.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                seconds=min(3600, 60 * 2 ** min(mapping.attempts, 6))
            )
            db.session.commit()
            current_app.logger.warning("CRM synchronization pending for supporter %s: %s",
                                       supporter_id, mapping.last_error)
    finally:
        if client is not None:
            client.close()


@shared_task(name="metabrainz.crm.tasks.requeue_pending_supporters")
def requeue_pending_supporters():
    if not current_app.config.get("CRM_ENABLED", False):
        return
    now = datetime.now(timezone.utc)
    rows = CrmSync.query.filter(
        CrmSync.pending.is_(True), CrmSync.next_attempt_at <= now,
    ).order_by(CrmSync.next_attempt_at).with_for_update(skip_locked=True).limit(100).all()
    ids = [row.supporter_id for row in rows]
    for row in rows:
        row.next_attempt_at = now + timedelta(minutes=10)
    db.session.commit()
    for supporter_id in ids:
        publish_signup_sync(supporter_id)
