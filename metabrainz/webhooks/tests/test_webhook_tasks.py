from datetime import datetime, timezone, timedelta

import requests_mock

from metabrainz.model import db
from metabrainz.model.webhook import Webhook, EVENT_USER_CREATED, EVENT_USER_UPDATED
from metabrainz.model.webhook_delivery import WebhookDelivery
from metabrainz.testing import FlaskTestCase
from metabrainz.webhooks.tasks import (
    deliver_webhook,
    retry_failed_webhooks,
    cleanup_old_deliveries
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

        delivery = WebhookDelivery(
            webhook_id=inactive_webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="failed",
            retry_count=1,
            next_retry_at=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        db.session.add(delivery)
        db.session.commit()

        result = retry_failed_webhooks()
        self.assertEqual(result["found"], 0)
        self.assertEqual(result["queued"], 0)

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
