from datetime import datetime, timezone, timedelta
from typing import Any

from celery import shared_task
from flask import current_app
from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError

from metabrainz.model import db
from metabrainz.model.webhook_delivery import (
    WebhookDelivery,
    WebhookDeliveryError,
)
from metabrainz.webhooks.delivery import WebhookDeliveryEngine


def release_processing_delivery(delivery_id: str, error_message: str) -> None:
    """Release a claimed delivery before Celery retries the task."""
    db.session.rollback()
    WebhookDelivery.query.filter(
        WebhookDelivery.id == delivery_id,
        WebhookDelivery.status == "processing",
    ).update(
        {
            WebhookDelivery.status: "pending",
            WebhookDelivery.error_message: error_message[:1000],
            WebhookDelivery.next_retry_at: None,
            WebhookDelivery.updated_at: datetime.now(timezone.utc),
        },
        synchronize_session=False,
    )
    db.session.commit()


@shared_task(
    bind=True,
    name="metabrainz.webhooks.tasks.deliver_webhook",
    max_retries=3,
    default_retry_delay=60,
)
def deliver_webhook(self, delivery_id: str):
    """
    Asynchronously deliver a webhook.

    This task is executed by Celery workers and handles the HTTP delivery
    of a webhook with proper error handling and retries.

    Args:
        delivery_id: UUID of the WebhookDelivery record

    Raises:
        Exception: Re-raised after retries are exhausted
    """
    try:
        current_app.logger.info(
            f"Starting webhook delivery {delivery_id} "
            f"(attempt {self.request.retries + 1})"
        )
        return WebhookDeliveryEngine.deliver(delivery_id)
    except SQLAlchemyError as e:
        current_app.logger.error(
            f"Database error during webhook delivery {delivery_id}: {e}",
            exc_info=True
        )
        try:
            release_processing_delivery(
                delivery_id,
                f"Database error during webhook delivery: {e}",
            )
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.error(
                "Could not return webhook delivery %s to a retryable state",
                delivery_id,
                exc_info=True,
            )
        raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)
    except WebhookDeliveryError as e:
        current_app.logger.warning(
            "Webhook delivery task %s was not run: %s",
            delivery_id,
            e,
        )
        return {
            "success": False,
            "delivery_id": delivery_id,
            "error": str(e),
        }
    except Exception as e:
        current_app.logger.error(
            f"Unexpected error during webhook delivery {delivery_id}: {e}",
            exc_info=True
        )

        try:
            release_processing_delivery(
                delivery_id,
                f"Unexpected error: {e}",
            )
        except Exception as update_error:
            current_app.logger.error(
                f"Failed to update delivery {delivery_id} after error: {update_error}"
            )
        raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)


def _publish_webhook_delivery(delivery_id, enqueued_at: datetime) -> None:
    """Publish a delivery task and recover safely if broker publication fails."""
    try:
        deliver_webhook.apply_async(
            args=[str(delivery_id)],
            queue="webhooks",
        )
    except Exception as error:
        db.session.rollback()
        retry_at = datetime.now(timezone.utc) + timedelta(seconds=30)
        WebhookDelivery.query.filter(
            WebhookDelivery.id == delivery_id,
            WebhookDelivery.status == "pending",
            WebhookDelivery.updated_at == enqueued_at,
        ).update(
            {
                WebhookDelivery.status: "failed",
                WebhookDelivery.error_message: (
                    f"Failed to enqueue webhook delivery: {error}"
                )[:1000],
                WebhookDelivery.next_retry_at: retry_at,
                WebhookDelivery.updated_at: datetime.now(timezone.utc),
            },
            synchronize_session=False,
        )
        db.session.commit()
        raise


def publish_new_webhook_delivery(delivery: WebhookDelivery) -> None:
    """Publish a newly committed pending delivery without another DB update."""
    if delivery.status != "pending":
        raise ValueError(
            f"Cannot publish new delivery in status {delivery.status}"
        )
    _publish_webhook_delivery(delivery.id, delivery.updated_at)


def _enqueue_webhook_delivery_if(
    delivery_id,
    *eligibility_conditions,
) -> bool:
    """
    Atomically make an eligible delivery pending, then publish its task.

    Duplicate queued tasks are safe because delivery workers atomically claim
    pending rows. The eligibility conditions only need to prevent a retry from
    resetting a completed or freshly claimed delivery.
    """
    enqueued_at = datetime.now(timezone.utc)
    transitioned = WebhookDelivery.query.filter(
        WebhookDelivery.id == delivery_id,
        *eligibility_conditions,
    ).update(
        {
            WebhookDelivery.status: "pending",
            WebhookDelivery.error_message: None,
            WebhookDelivery.next_retry_at: None,
            WebhookDelivery.updated_at: enqueued_at,
        },
        synchronize_session=False,
    )
    db.session.commit()

    if not transitioned:
        return False

    _publish_webhook_delivery(delivery_id, enqueued_at)
    return True


def enqueue_webhook_delivery(delivery: WebhookDelivery) -> bool:
    """Queue an administrator-requested retry if it has not been claimed."""
    return _enqueue_webhook_delivery_if(
        delivery.id,
        WebhookDelivery.status.in_(["failed", "pending"]),
    )


@shared_task(name="metabrainz.webhooks.tasks.retry_failed_webhooks")
def retry_failed_webhooks() -> dict[str, Any]:
    """
    Periodic task to find and re-queue failed webhook deliveries.

    This task runs periodically (e.g., every 5 minutes) to find deliveries
    that are ready for retry and queues them for delivery.

    Returns:
        dictionary with retry statistics
    """
    try:
        current_app.logger.info("Starting webhook retry scheduler")

        now = datetime.now(timezone.utc)
        pending_timeout = current_app.config.get(
            "WEBHOOK_PENDING_DELIVERY_TIMEOUT",
            600,
        )
        processing_timeout = current_app.config.get(
            "WEBHOOK_PROCESSING_DELIVERY_TIMEOUT",
            300,
        )
        stale_pending_before = now - timedelta(
            seconds=pending_timeout,
        )
        stale_processing_before = now - timedelta(
            seconds=processing_timeout,
        )
        retry_eligibility = or_(
            and_(
                WebhookDelivery.status == "failed",
                WebhookDelivery.next_retry_at.isnot(None),
                WebhookDelivery.next_retry_at <= now,
            ),
            and_(
                WebhookDelivery.status == "pending",
                WebhookDelivery.updated_at <= stale_pending_before,
            ),
            and_(
                WebhookDelivery.status == "processing",
                WebhookDelivery.updated_at <= stale_processing_before,
            ),
        )
        delivery_ids_to_retry = WebhookDelivery.query.filter(
            WebhookDelivery.webhook.has(is_active=True),
            retry_eligibility,
        ).with_entities(
            WebhookDelivery.id,
        ).limit(1000).all()

        queued_count = 0
        error_count = 0

        for delivery_id, in delivery_ids_to_retry:
            try:
                if _enqueue_webhook_delivery_if(
                    delivery_id,
                    WebhookDelivery.webhook.has(is_active=True),
                    retry_eligibility,
                ):
                    queued_count += 1
            except Exception as e:
                error_count += 1
                current_app.logger.error(
                    f"Failed to re-queue delivery {delivery_id}: {e}",
                    exc_info=True,
                )

        result = {
            "found": len(delivery_ids_to_retry),
            "queued": queued_count,
            "errors": error_count,
        }

        current_app.logger.info(
            f"Webhook retry scheduler completed: {result}"
        )

        return result

    except Exception as e:
        current_app.logger.error(
            f"Error in webhook retry scheduler: {e}",
            exc_info=True
        )
        return {
            "found": 0,
            "queued": 0,
            "errors": 1,
            "error": str(e),
        }


@shared_task(name="metabrainz.webhooks.tasks.cleanup_old_deliveries")
def cleanup_old_deliveries(days: int = 7):
    """
    Clean up old webhook delivery records.

    This task removes old delivery records to prevent database bloat.
    Only successful deliveries older than the specified days are removed.

    Args:
        days: Number of days to keep delivery records (default 7)

    Returns:
        dictionary with cleanup statistics
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        deleted = WebhookDelivery.query.filter(
            WebhookDelivery.status == "delivered",
            WebhookDelivery.created_at < cutoff_date
        ).delete(synchronize_session=False)
        db.session.commit()
        current_app.logger.info(
            f"Cleaned up {deleted} webhook deliveries older than {days} days"
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Error during webhook delivery cleanup: {e}",
            exc_info=True
        )
