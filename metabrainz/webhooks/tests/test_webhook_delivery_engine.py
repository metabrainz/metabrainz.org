import json
from datetime import datetime, timezone

import requests_mock

from metabrainz.model import db
from metabrainz.model.webhook import Webhook, EVENT_USER_CREATED
from metabrainz.model.webhook_delivery import WebhookDelivery, WebhookDeliveryError
from metabrainz.testing import FlaskTestCase
from metabrainz.webhooks.circuit_breaker import CircuitBreakerState
from metabrainz.webhooks.delivery import WebhookDeliveryEngine


class WebhookDeliveryEngineTestCase(FlaskTestCase):
    """Test cases for WebhookDeliveryEngine."""

    def setUp(self):
        super().setUp()
        self.webhook = Webhook(
            name="Test Webhook",
            url="https://example.com/webhook",
            secret="mebw_test_secret",
            events=[EVENT_USER_CREATED],
            is_active=True
        )
        db.session.add(self.webhook)
        db.session.commit()

        self.payload = {
            "user_id": 123,
            "username": "test_user",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        WebhookDeliveryEngine._circuit_breakers.clear()

    def test_get_circuit_breaker_creates_per_webhook(self):
        """Test that each webhook gets its own circuit breaker."""
        cb1 = WebhookDeliveryEngine.get_circuit_breaker(self.webhook.id)
        cb2 = WebhookDeliveryEngine.get_circuit_breaker(self.webhook.id)
        self.assertIs(cb1, cb2)

        webhook2 = Webhook(
            name="Webhook 2",
            url="https://example.com/webhook2",
            secret="secret2",
            events=[EVENT_USER_CREATED],
            is_active=True
        )
        db.session.add(webhook2)
        db.session.commit()

        cb3 = WebhookDeliveryEngine.get_circuit_breaker(webhook2.id)
        self.assertIsNot(cb1, cb3)

    @requests_mock.Mocker()
    def test_deliver_success(self, mock_requests):
        """Test successful webhook delivery."""
        mock_requests.post(
            "https://example.com/webhook",
            status_code=200,
            text='{"success": true}',
            headers={"Content-Type": "application/json"}
        )

        delivery = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="pending"
        )
        db.session.add(delivery)
        db.session.commit()

        result = WebhookDeliveryEngine.deliver(str(delivery.id))

        self.assertTrue(result["success"])
        self.assertEqual(result["delivery_id"], str(delivery.id))

        db.session.refresh(delivery)
        self.assertEqual(delivery.status, "delivered")
        self.assertEqual(delivery.response_status, 200)
        self.assertIsNotNone(delivery.response_body)

        request = mock_requests.last_request
        headers = request.headers

        self.assertEqual(headers["User-Agent"], "MetaBrainz-Webhooks/1.0")
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(headers["X-MetaBrainz-Event"], EVENT_USER_CREATED)
        self.assertEqual(headers["X-MetaBrainz-Delivery"], str(delivery.id))
        self.assertEqual(headers["X-MetaBrainz-Attempt"], "1")
        self.assertIn("X-MetaBrainz-Signature-256", headers)
        self.assertTrue(headers["X-MetaBrainz-Signature-256"].startswith("sha256="))

        sent_data = request.body
        self.assertIsInstance(sent_data, bytes)
        payload_dict = json.loads(sent_data.decode("utf-8"))
        self.assertEqual(payload_dict, self.payload)

    @requests_mock.Mocker()
    def test_deliver_http_error(self, mock_requests):
        """Test webhook delivery with HTTP error."""
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

        result = WebhookDeliveryEngine.deliver(str(delivery.id))

        self.assertFalse(result["success"])
        self.assertEqual(result["delivery_id"], str(delivery.id))
        self.assertIn("error", result)
        self.assertTrue(result["will_retry"])

        db.session.refresh(delivery)
        self.assertEqual(delivery.status, "failed")
        self.assertEqual(delivery.response_status, 500)
        self.assertIsNotNone(delivery.error_message)
        self.assertIsNotNone(delivery.next_retry_at)
        self.assertGreater(delivery.next_retry_at, datetime.now(timezone.utc))

    @requests_mock.Mocker()
    def test_deliver_connection_error(self, mock_requests):
        """Test webhook delivery with connection error."""
        mock_requests.post(
            "https://example.com/webhook",
            exc=ConnectionError("Connection refused")
        )

        delivery = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="pending"
        )
        db.session.add(delivery)
        db.session.commit()

        result = WebhookDeliveryEngine.deliver(str(delivery.id))

        self.assertFalse(result["success"])
        self.assertIn("Connection refused", result["error"])

        db.session.refresh(delivery)
        self.assertEqual(delivery.status, "failed")
        self.assertIn("Connection refused", delivery.error_message)

    def test_deliver_nonexistent_delivery(self):
        """Test delivering a nonexistent delivery raises error."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        with self.assertRaises(WebhookDeliveryError) as context:
            WebhookDeliveryEngine.deliver(fake_id)

        self.assertIn("not found", str(context.exception))

    def test_deliver_inactive_webhook(self):
        """Test delivering to an inactive webhook."""
        self.webhook.is_active = False
        db.session.commit()

        delivery = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="pending"
        )
        db.session.add(delivery)
        db.session.commit()

        with self.assertRaises(WebhookDeliveryError) as context:
            WebhookDeliveryEngine.deliver(str(delivery.id))

        self.assertIn("not active", str(context.exception))
        db.session.refresh(delivery)
        self.assertEqual(delivery.status, "failed")
        self.assertIn("not active", delivery.error_message)

    @requests_mock.Mocker()
    def test_deliver_with_circuit_breaker_open(self, mock_requests):
        """Test that delivery is blocked when circuit breaker is open."""
        cb = WebhookDeliveryEngine.get_circuit_breaker(self.webhook.id)
        for _ in range(5):
            cb.record_failure()
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)

        delivery = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="pending"
        )
        db.session.add(delivery)
        db.session.commit()

        result = WebhookDeliveryEngine.deliver(str(delivery.id))

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Circuit breaker open")
        self.assertTrue(result["will_retry"])

        db.session.refresh(delivery)
        self.assertEqual(delivery.status, "failed")
        self.assertIn("Circuit breaker", delivery.error_message)
        self.assertIsNotNone(delivery.next_retry_at)

        self.assertEqual(len(mock_requests.request_history), 0)

    @requests_mock.Mocker()
    def test_circuit_breaker_records_success(self, mock_requests):
        """Test that successful delivery records success in circuit breaker."""
        mock_requests.post(
            "https://example.com/webhook",
            status_code=200,
            text='{"success": true}'
        )

        cb = WebhookDeliveryEngine.get_circuit_breaker(self.webhook.id)

        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb._failure_count, 2)

        delivery = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="pending"
        )
        db.session.add(delivery)
        db.session.commit()

        WebhookDeliveryEngine.deliver(str(delivery.id))

        self.assertEqual(cb._failure_count, 0)

    @requests_mock.Mocker()
    def test_circuit_breaker_records_failure(self, mock_requests):
        """Test that failed delivery records failure in circuit breaker."""
        mock_requests.post(
            "https://example.com/webhook",
            status_code=500,
            text="Error"
        )

        cb = WebhookDeliveryEngine.get_circuit_breaker(self.webhook.id)
        initial_count = cb._failure_count

        delivery = WebhookDelivery(
            webhook_id=self.webhook.id,
            event_type=EVENT_USER_CREATED,
            payload=self.payload,
            status="pending"
        )
        db.session.add(delivery)
        db.session.commit()

        WebhookDeliveryEngine.deliver(str(delivery.id))

        self.assertEqual(cb._failure_count, initial_count + 1)
