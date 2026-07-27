from datetime import datetime, timezone, timedelta
from typing import Any

from celery import shared_task
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from metabrainz.model import db
from metabrainz.model.webhook_delivery import WebhookDelivery
from metabrainz.webhooks.delivery import WebhookDeliveryEngine


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
        WebhookDeliveryEngine.deliver(delivery_id)
    except SQLAlchemyError as e:
        current_app.logger.error(
            f"Database error during webhook delivery {delivery_id}: {e}",
            exc_info=True
        )
        raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)
    except Exception as e:
        current_app.logger.error(
            f"Unexpected error during webhook delivery {delivery_id}: {e}",
            exc_info=True
        )

        try:
            delivery = WebhookDelivery.query.get(delivery_id)
            if delivery and delivery.status in ["pending", "processing"]:
                delivery.status = "failed"
                delivery.error_message = f"Unexpected error: {str(e)}"
                delivery.schedule_retry()
                delivery.updated_at = datetime.now(timezone.utc)
                db.session.commit()
        except Exception as update_error:
            current_app.logger.error(
                f"Failed to update delivery {delivery_id} after error: {update_error}"
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
        deliveries_to_retry = WebhookDelivery.query.filter(
            WebhookDelivery.webhook.has(is_active=True),
            WebhookDelivery.status == "failed",
            WebhookDelivery.next_retry_at.isnot(None),
            WebhookDelivery.next_retry_at <= now
        ).limit(1000).all()

        queued_count = 0
        error_count = 0

        for delivery in deliveries_to_retry:
            try:
                delivery.status = "pending"
                delivery.updated_at = datetime.now(timezone.utc)
                db.session.commit()

                deliver_webhook.apply_async(
                    args=[str(delivery.id)],
                    queue="webhooks"
                )

                queued_count += 1
            except Exception as e:
                error_count += 1
                current_app.logger.error(
                    f"Failed to re-queue delivery {delivery.id}: {e}",
                    exc_info=True
                )

        result = {
            "found": len(deliveries_to_retry),
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
