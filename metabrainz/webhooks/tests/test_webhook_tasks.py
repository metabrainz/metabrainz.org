from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import requests_mock

from metabrainz.model import db
from metabrainz.model.webhook import Webhook, EVENT_USER_CREATED, EVENT_USER_UPDATED
from metabrainz.model.webhook_delivery import WebhookDelivery
from metabrainz.testing import FlaskTestCase
from metabrainz.webhooks import tasks as webhook_tasks
from metabrainz.webhooks.tasks import (
    deliver_webhook,
    retry_failed_webhooks,
    cleanup_old_deliveries,
    enqueue_webhook_delivery,
    publish_new_webhook_delivery,
)


class WebhookTasksTestCase(FlaskTestCase):
    """Test cases for webhook Celery tasks."""

    def setUp(self):
        super().setUp()

        self.webhook = Webhook(
            name="Test Webhook",
            url="https://example.com/webhook",
            secret="mebw_test_secret",
            events=[EVENT_USER_CREATED, EVENT_USER_UPDATED],
            is_active=True
        )
        db.session.add(self.webhook)
        db.session.commit()

        self.payload = {
            "user_id": 123,
            "username": "test_user",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @requests_mock.Mocker()
    def test_deliver_webhook_task_success(self, mock_requests):
        """Test deliver_webhook task with successful delivery."""
        mock_requests.post(
            "https://example.com/webhook",
            status_code=200,
            text='{"success": true}'
        )

        delivery = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="pending"
        )
        db.session.add(delivery)
        db.session.commit()

        deliver_webhook(str(delivery.id))

        db.session.refresh(delivery)
        self.assertEqual(delivery.status, "delivered")

    @requests_mock.Mocker()
    def test_deliver_webhook_task_failure_with_retry(self, mock_requests):
        """Test deliver_webhook task with failed delivery that will be retried."""
        mock_requests.post(
            "https://example.com/webhook",
            status_code=500,
            text="Internal Server Error"
        )

        delivery = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="pending"
        )
        db.session.add(delivery)
        db.session.commit()

        deliver_webhook(str(delivery.id))

        db.session.refresh(delivery)
        self.assertEqual(delivery.status, "failed")
        self.assertIsNotNone(delivery.next_retry_at)

    @requests_mock.Mocker()
    def test_retry_failed_webhooks_task(self, mock_requests):
        """Test retry_failed_webhooks periodic task."""
        mock_requests.post(
            self.webhook.url,
            status_code=500,
            text="Internal Server Error"
        )
        now = datetime.now(timezone.utc)

        delivery1 = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="failed",
            retry_count=1,
            next_retry_at=now - timedelta(minutes=5)
        )

        delivery2 = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_UPDATED,
            payload=self.payload,
            status="failed",
            retry_count=2,
            next_retry_at=now - timedelta(minutes=1)
        )

        delivery3 = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="failed",
            retry_count=1,
            next_retry_at=now + timedelta(minutes=10)
        )

        db.session.add_all([delivery1, delivery2, delivery3])
        db.session.commit()

        result = retry_failed_webhooks()

        self.assertEqual(result["found"], 2)
        self.assertEqual(result["queued"], 2)
        self.assertEqual(result["errors"], 0)

        db.session.expire_all()

        self.assertEqual(delivery1.status, "pending")
        self.assertEqual(delivery2.status, "pending")
        self.assertEqual(delivery3.status, "failed")

    def test_retry_failed_webhooks_inactive_webhook(self):
        """Test that retry_failed_webhooks ignores inactive webhooks."""
        inactive_webhook = Webhook(
            name="Inactive Webhook",
            url="https://example.com/inactive",
            secret="secret",
            events=[EVENT_USER_CREATED],
            is_active=False
        )
        db.session.add(inactive_webhook)
        db.session.commit()

        now = datetime.now(timezone.utc)
        deliveries = [
            WebhookDelivery(
                webhook_id=inactive_webhook.id,
                event_type=EVENT_USER_CREATED,
                payload=self.payload,
                status="failed",
                retry_count=1,
                next_retry_at=now - timedelta(minutes=5),
            ),
            WebhookDelivery(
                webhook_id=inactive_webhook.id,
                event_type=EVENT_USER_CREATED,
                payload=self.payload,
                status="pending",
                updated_at=now - timedelta(minutes=20),
            ),
            WebhookDelivery(
                webhook_id=inactive_webhook.id,
                event_type=EVENT_USER_CREATED,
                payload=self.payload,
                status="processing",
                updated_at=now - timedelta(minutes=10),
            ),
        ]
        db.session.add_all(deliveries)
        db.session.commit()

        result = retry_failed_webhooks()
        self.assertEqual(result["found"], 0)
        self.assertEqual(result["queued"], 0)
        self.assertEqual(result["errors"], 0)

    def test_cleanup_old_deliveries_task(self):
        """Test cleanup_old_deliveries periodic task."""
        now = datetime.now(timezone.utc)

        old_delivery = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="delivered",
            created_at=now - timedelta(days=10)
        )

        recent_delivery = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="delivered"
        )

        old_failed = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="failed",
            created_at=now - timedelta(days=10)
        )

        db.session.add_all([old_delivery, recent_delivery, old_failed])
        db.session.commit()

        old_delivery_id = old_delivery.id
        recent_delivery_id = recent_delivery.id
        old_failed_id = old_failed.id

        cleanup_old_deliveries(days=7)

        db.session.expire_all()

        deleted = db.session.get(WebhookDelivery, {"id": old_delivery_id})
        self.assertIsNone(deleted)

        recent = db.session.get(WebhookDelivery, {"id": recent_delivery_id})
        self.assertIsNotNone(recent)

        failed = db.session.get(WebhookDelivery, {"id": old_failed_id})
        self.assertIsNotNone(failed)

    def test_retry_failed_webhooks_empty_result(self):
        """Test retry_failed_webhooks when there are no failed deliveries."""
        result = retry_failed_webhooks()

        self.assertEqual(result["found"], 0)
        self.assertEqual(result["queued"], 0)
        self.assertEqual(result["errors"], 0)

    def test_enqueue_failure_restores_retryable_failed_state(self):
        """A broker failure must not orphan a pending delivery."""
        delivery = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="pending",
        )
        db.session.add(delivery)
        db.session.commit()

        with patch.object(
            deliver_webhook,
            "apply_async",
            side_effect=RuntimeError("broker unavailable"),
        ):
            with self.assertRaisesRegex(RuntimeError, "broker unavailable"):
                enqueue_webhook_delivery(delivery)

        db.session.refresh(delivery)
        self.assertEqual(delivery.status, "failed")
        self.assertEqual(delivery.retry_count, 0)
        self.assertIsNotNone(delivery.next_retry_at)
        self.assertIn("Failed to enqueue", delivery.error_message)

    def test_new_delivery_publish_does_not_update_database_state(self):
        """Publishing a newly created delivery does not need a DB transition."""
        delivery = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="pending",
        )
        db.session.add(delivery)
        db.session.commit()
        original_updated_at = delivery.updated_at

        with patch.object(deliver_webhook, "apply_async") as apply_async:
            publish_new_webhook_delivery(delivery)

        apply_async.assert_called_once_with(
            args=[str(delivery.id)],
            queue="webhooks",
        )
        db.session.refresh(delivery)
        self.assertEqual(delivery.status, "pending")
        self.assertEqual(delivery.updated_at, original_updated_at)

    def test_stale_retry_cannot_resurrect_completed_delivery(self):
        """A stale retry caller must not overwrite a newer delivery state."""
        delivery = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="failed",
            next_retry_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        db.session.add(delivery)
        db.session.commit()

        delivery_id = delivery.id
        expected_updated_at = delivery.updated_at
        db.session.expunge(delivery)

        WebhookDelivery.query.filter(
            WebhookDelivery.id == delivery_id,
        ).update(
            {
                WebhookDelivery.status: "delivered",
                WebhookDelivery.updated_at: datetime.now(timezone.utc),
            },
            synchronize_session=False,
        )
        db.session.commit()

        stale_delivery = WebhookDelivery(
            id=delivery_id,
            status="failed",
            updated_at=expected_updated_at,
        )
        with patch.object(deliver_webhook, "apply_async") as apply_async:
            queued = enqueue_webhook_delivery(stale_delivery)

        self.assertFalse(queued)
        apply_async.assert_not_called()
        current_delivery = db.session.get(
            WebhookDelivery,
            {"id": delivery_id},
        )
        self.assertEqual(current_delivery.status, "delivered")

    def test_retry_task_recovers_stale_pending_delivery(self):
        """Pending rows that were never claimed are eventually requeued."""
        delivery = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="pending",
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=20),
        )
        db.session.add(delivery)
        db.session.commit()

        with patch.object(deliver_webhook, "apply_async") as apply_async:
            result = retry_failed_webhooks()

        self.assertEqual(result["found"], 1)
        self.assertEqual(result["queued"], 1)
        apply_async.assert_called_once_with(
            args=[str(delivery.id)],
            queue="webhooks",
        )

    def test_retry_task_recovers_stale_processing_delivery(self):
        """Rows abandoned by a dead worker are eventually requeued."""
        delivery = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="processing",
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )
        db.session.add(delivery)
        db.session.commit()

        with patch.object(deliver_webhook, "apply_async") as apply_async:
            result = retry_failed_webhooks()

        self.assertEqual(result["found"], 1)
        self.assertEqual(result["queued"], 1)
        apply_async.assert_called_once_with(
            args=[str(delivery.id)],
            queue="webhooks",
        )

    def test_retry_task_does_not_reset_freshly_claimed_delivery(self):
        """Retry eligibility is checked again during the pending transition."""
        delivery = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="pending",
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=20),
        )
        db.session.add(delivery)
        db.session.commit()

        enqueue_if_eligible = webhook_tasks._enqueue_webhook_delivery_if

        def claim_before_retry(delivery_id, *eligibility_conditions):
            WebhookDelivery.query.filter(
                WebhookDelivery.id == delivery_id,
            ).update(
                {
                    WebhookDelivery.status: "processing",
                    WebhookDelivery.updated_at: datetime.now(timezone.utc),
                },
                synchronize_session=False,
            )
            db.session.commit()
            return enqueue_if_eligible(delivery_id, *eligibility_conditions)

        with (
            patch.object(
                webhook_tasks,
                "_enqueue_webhook_delivery_if",
                side_effect=claim_before_retry,
            ),
            patch.object(deliver_webhook, "apply_async") as apply_async,
        ):
            result = retry_failed_webhooks()

        self.assertEqual(result["found"], 1)
        self.assertEqual(result["queued"], 0)
        apply_async.assert_not_called()
        db.session.refresh(delivery)
        self.assertEqual(delivery.status, "processing")
