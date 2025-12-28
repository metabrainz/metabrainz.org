import hashlib
import hmac
import json
from datetime import datetime

import requests_mock
from brainzutils import cache
from flask import g, url_for

from metabrainz.model import db
from metabrainz.model.user import User
from metabrainz.model.webhook import (
    Webhook,
    EVENT_USER_CREATED,
    EVENT_USER_DELETED,
    EVENT_USER_UPDATED
)
from metabrainz.model.webhook_delivery import WebhookDelivery
from metabrainz.testing import FlaskTestCase
from metabrainz.user.email import create_email_link_checksum, VERIFY_EMAIL
from metabrainz.webhooks.delivery import WebhookDeliveryEngine


class WebhookIntegrationTestCase(FlaskTestCase):

    @classmethod
    def create_app(cls):
        app = super().create_app()
        app.extensions["celery"].conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return app

    def setUp(self):
        super().setUp()
        WebhookDeliveryEngine._circuit_breakers.clear()

    def tearDown(self):
        cache._r.flushall()
        super().tearDown()

    @requests_mock.Mocker(real_http=False)
    def test_user_signup_triggers_webhook(self, mock_requests):
        """Test that user signup triggers webhook with correct payload."""
        webhook = Webhook(
            name="User Events Webhook",
            url="https://example.com/webhooks/user-events",
            secret="mebw_secret_key",
            events=[EVENT_USER_CREATED, EVENT_USER_UPDATED],
            is_active=True
        )
        db.session.add(webhook)
        db.session.commit()

        mock_requests.post(
            "https://example.com/webhooks/user-events",
            status_code=200,
            text='{"received": true}'
        )

        self.client.get("/signup")
        response = self.client.post("/signup", data={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "csrf_token": g.csrf_token
        })

        self.assertEqual(response.status_code, 302)

        deliveries = WebhookDelivery.query.filter_by(
            webhook_id=webhook.id,
            event_type=EVENT_USER_CREATED
        ).all()

        self.assertEqual(len(deliveries), 1)
        delivery = deliveries[0]

        self.assertIn("user_id", delivery.payload)
        self.assertIn("name", delivery.payload)
        self.assertEqual(delivery.payload["name"], "newuser")

        self.assertEqual(len(mock_requests.request_history), 1)
        request = mock_requests.last_request
        self.assertEqual(request.headers["X-MetaBrainz-Event"], EVENT_USER_CREATED)
        self.assertIn("X-MetaBrainz-Signature-256", request.headers)
        self.assertEqual(delivery.status, "delivered")
        self.assertEqual(delivery.response_status, 200)

    @requests_mock.Mocker()
    def test_email_verification_triggers_webhook(self, mock_requests):
        """Test that email verification triggers user.updated webhook."""
        webhook = Webhook(
            name="User Updated Webhook",
            url="https://example.com/webhooks/updated",
            secret="mebw_secret",
            events=[EVENT_USER_UPDATED],
            is_active=True
        )
        db.session.add(webhook)
        db.session.commit()

        mock_requests.post(
            "https://example.com/webhooks/updated",
            status_code=200,
            text="OK"
        )

        self.client.get("/signup")
        response = self.client.post("/signup", data={
            "username": "verifyuser",
            "email": "verify@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "csrf_token": g.csrf_token
        })

        # the last template rendered is the verification email, so we can get it from the context
        verification_link = self.get_context_variable("verification_link")

        WebhookDelivery.query.delete()
        db.session.commit()
        mock_requests.reset_mock()

        response = self.client.get(verification_link)
        self.assertEqual(response.status_code, 302)

        deliveries = WebhookDelivery.query.filter_by(
            webhook_id=webhook.id,
            event_type=EVENT_USER_UPDATED
        ).all()

        self.assertEqual(len(deliveries), 1)
        delivery = deliveries[0]

        self.assertIn("user_id", delivery.payload)
        self.assertIn("old", delivery.payload)
        self.assertIn("new", delivery.payload)
        self.assertEqual(delivery.payload["new"]["email"], "verify@example.com")

        self.assertEqual(len(mock_requests.request_history), 1)
        self.assertEqual(delivery.status, "delivered")

    @requests_mock.Mocker()
    def test_multiple_webhooks_receive_same_event(self, mock_requests):
        """Test that multiple webhooks subscribed to the same event all receive it."""
        webhook1 = Webhook(
            name="Webhook 1",
            url="https://example.com/webhook1",
            secret="secret1",
            events=[EVENT_USER_CREATED],
            is_active=True
        )
        webhook2 = Webhook(
            name="Webhook 2",
            url="https://api.example.org/hooks",
            secret="secret2",
            events=[EVENT_USER_CREATED, EVENT_USER_UPDATED],
            is_active=True
        )
        webhook3 = Webhook(
            name="Webhook 3",
            url="https://hooks.example.net/receive",
            secret="secret3",
            events=[EVENT_USER_CREATED],
            is_active=True
        )

        db.session.add_all([webhook1, webhook2, webhook3])
        db.session.commit()

        mock_requests.post("https://example.com/webhook1", status_code=200, text="OK")
        mock_requests.post("https://api.example.org/hooks", status_code=200, text="OK")
        mock_requests.post("https://hooks.example.net/receive", status_code=200, text="OK")

        self.client.get("/signup")
        self.client.post("/signup", data={
            "username": "multiuser",
            "email": "multi@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "csrf_token": g.csrf_token
        })

        deliveries = WebhookDelivery.query.filter_by(
            event_type=EVENT_USER_CREATED
        ).all()

        self.assertEqual(len(deliveries), 3)

        webhook_ids = [d.webhook_id for d in deliveries]
        self.assertIn(webhook1.id, webhook_ids)
        self.assertIn(webhook2.id, webhook_ids)
        self.assertIn(webhook3.id, webhook_ids)

        for delivery in deliveries:
            self.assertEqual(delivery.status, "delivered")

        self.assertEqual(len(mock_requests.request_history), 3)

    @requests_mock.Mocker()
    def test_inactive_webhook_does_not_receive_events(self, mock_requests):
        """Test that inactive webhooks do not receive events from user signup."""
        active_webhook = Webhook(
            name="Active Webhook",
            url="https://example.com/active",
            secret="secret1",
            events=[EVENT_USER_CREATED],
            is_active=True
        )
        inactive_webhook = Webhook(
            name="Inactive Webhook",
            url="https://example.com/inactive",
            secret="secret2",
            events=[EVENT_USER_CREATED],
            is_active=False
        )

        db.session.add_all([active_webhook, inactive_webhook])
        db.session.commit()

        mock_requests.post("https://example.com/active", status_code=200, text="OK")
        mock_requests.post("https://example.com/inactive", status_code=200, text="OK")

        self.client.get("/signup")
        self.client.post("/signup", data={
            "username": "inactivetest",
            "email": "inactive@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "csrf_token": g.csrf_token
        })

        deliveries = WebhookDelivery.query.filter_by(
            event_type=EVENT_USER_CREATED
        ).all()

        self.assertEqual(len(deliveries), 1)
        self.assertEqual(deliveries[0].webhook_id, active_webhook.id)

        self.assertEqual(len(mock_requests.request_history), 1)
        self.assertEqual(mock_requests.last_request.url, "https://example.com/active")

    @requests_mock.Mocker()
    def test_webhook_retry_on_failure(self, mock_requests):
        """Test that failed webhooks are retried."""
        webhook = Webhook(
            name="Retry Test Webhook",
            url="https://example.com/webhook",
            secret="secret",
            events=[EVENT_USER_CREATED],
            is_active=True
        )
        db.session.add(webhook)
        db.session.commit()

        mock_requests.post(
            "https://example.com/webhook",
            [
                {"status_code": 500, "text": "Error"},
                {"status_code": 200, "text": "OK"}
            ]
        )

        self.client.get("/signup")
        self.client.post("/signup", data={
            "username": "retryuser",
            "email": "retry@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "csrf_token": g.csrf_token
        })

        db.session.expire_all()

        deliveries = WebhookDelivery.query.all()
        self.assertEqual(len(deliveries), 1)
        delivery = deliveries[0]

        self.assertEqual(delivery.status, "failed")
        self.assertIsNotNone(delivery.next_retry_at)
        self.assertEqual(delivery.retry_count, 1)

        delivery.status = "pending"
        db.session.commit()

        result = WebhookDeliveryEngine.deliver(str(delivery.id))

        self.assertTrue(result["success"])
        db.session.refresh(delivery)
        self.assertEqual(delivery.status, "delivered")

    @requests_mock.Mocker()
    def test_event_filtering_by_subscription(self, mock_requests):
        """Test that webhooks only receive events they're subscribed to."""
        webhook1 = Webhook(
            name="Webhook 1",
            url="https://example.com/webhook1",
            secret="secret1",
            events=[EVENT_USER_CREATED],
            is_active=True
        )

        webhook2 = Webhook(
            name="Webhook 2",
            url="https://example.com/webhook2",
            secret="secret2",
            events=[EVENT_USER_UPDATED],
            is_active=True
        )

        db.session.add_all([webhook1, webhook2])
        db.session.commit()

        mock_requests.post("https://example.com/webhook1", status_code=200, text="OK")
        mock_requests.post("https://example.com/webhook2", status_code=200, text="OK")

        self.client.get("/signup")
        self.client.post("/signup", data={
            "username": "filteruser",
            "email": "filter@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "csrf_token": g.csrf_token
        })

        deliveries = WebhookDelivery.query.all()
        self.assertEqual(len(deliveries), 1)
        self.assertEqual(deliveries[0].webhook_id, webhook1.id)
        self.assertEqual(deliveries[0].event_type, EVENT_USER_CREATED)

        self.assertEqual(len(mock_requests.request_history), 1)
        self.assertEqual(mock_requests.last_request.url, "https://example.com/webhook1")

    @requests_mock.Mocker()
    def test_webhook_signature_verification(self, mock_requests):
        """Test that webhook signature is correctly generated and sent."""
        webhook = Webhook(
            name="Signature Test",
            url="https://example.com/webhook",
            secret="test_secret_key",
            events=[EVENT_USER_CREATED],
            is_active=True
        )
        db.session.add(webhook)
        db.session.commit()

        mock_requests.post("https://example.com/webhook", status_code=200, text="OK")

        self.client.get("/signup")
        self.client.post("/signup", data={
            "username": "siguser",
            "email": "sig@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "csrf_token": g.csrf_token
        })

        self.assertEqual(len(mock_requests.request_history), 1)
        request = mock_requests.last_request
        headers = request.headers
        sent_signature = headers["X-MetaBrainz-Signature-256"]

        self.assertTrue(sent_signature.startswith("sha256="))

        sent_data = request.body
        expected_signature = hmac.new(
            key=b"test_secret_key",
            msg=sent_data,
            digestmod=hashlib.sha256
        ).hexdigest()

        self.assertEqual(sent_signature, f"sha256={expected_signature}")

    @requests_mock.Mocker()
    def test_concurrent_deliveries_to_same_webhook(self, mock_requests):
        """Test multiple users signing up triggers multiple deliveries."""
        self.app.config["SIGNUP_RATE_LIMIT_PER_IP"] = 5
        webhook = Webhook(
            name="Concurrent Test Webhook",
            url="https://example.com/webhook",
            secret="secret",
            events=[EVENT_USER_CREATED],
            is_active=True
        )
        db.session.add(webhook)
        db.session.commit()

        mock_requests.post("https://example.com/webhook", status_code=200, text="OK")

        for i in range(3):
            self.client.get("/signup")
            response = self.client.post("/signup", data={
                "username": f"user{i}",
                "email": f"user{i}@example.com",
                "password": "password123",
                "confirm_password": "password123",
                "csrf_token": g.csrf_token
            })
            self.assertStatus(response, 302)
            self.client.get("/logout")

        deliveries = WebhookDelivery.query.filter_by(webhook_id=webhook.id).all()
        self.assertEqual(len(deliveries), 3)

        for delivery in deliveries:
            self.assertEqual(delivery.status, "delivered")

        self.assertEqual(len(mock_requests.request_history), 3)

    @requests_mock.Mocker()
    def test_user_deleted_via_profile_triggers_webhook(self, mock_requests):
        """Test that user self-deletion via profile triggers webhook with correct payload."""
        webhook = Webhook(
            name="User Deleted Webhook",
            url="https://example.com/webhooks/user-events",
            secret="mebw_secret_key",
            events=[EVENT_USER_DELETED],
            is_active=True
        )
        db.session.add(webhook)
        db.session.commit()

        mock_requests.post(
            "https://example.com/webhooks/user-events",
            status_code=200,
            text='{"received": true}'
        )

        self.client.get("/signup")
        self.client.post("/signup", data={
            "username": "deleteuser",
            "email": "delete@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "csrf_token": g.csrf_token
        })

        user = User.get(name="deleteuser")
        user_id = user.id

        WebhookDelivery.query.delete()
        db.session.commit()
        mock_requests.reset_mock()

        self.client.get("/profile/delete")
        response = self.client.post("/profile/delete", data={
            "csrf_token": g.csrf_token
        })
        self.assertEqual(response.status_code, 302)

        deliveries = WebhookDelivery.query.filter_by(
            webhook_id=webhook.id,
            event_type=EVENT_USER_DELETED
        ).all()

        self.assertEqual(len(deliveries), 1)
        delivery = deliveries[0]

        self.assertEqual(len(mock_requests.request_history), 1)
        request = mock_requests.last_request
        self.assertEqual(request.headers["X-MetaBrainz-Event"], EVENT_USER_DELETED)

        body = json.loads(request.body)
        self.assertEqual(body["user_id"], user_id)
        self.assertEqual(body["reason"], "User requested account deletion")
        self.assertEqual(delivery.status, "delivered")

    @requests_mock.Mocker()
    def test_user_email_change_via_profile_triggers_webhook(self, mock_requests):
        """Test that email change via profile and verification triggers webhook."""
        webhook = Webhook(
            name="User Updated Webhook",
            url="https://example.com/webhooks/user-events",
            secret="mebw_secret_key",
            events=[EVENT_USER_UPDATED],
            is_active=True
        )
        db.session.add(webhook)
        db.session.commit()

        mock_requests.post(
            "https://example.com/webhooks/user-events",
            status_code=200,
            text='{"received": true}'
        )

        # Create user and verify initial email
        self.client.get("/signup")
        self.client.post("/signup", data={
            "username": "emailchangeuser",
            "email": "old@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "csrf_token": g.csrf_token
        })

        verification_link = self.get_context_variable("verification_link")
        self.client.get(verification_link)

        user = User.get(name="emailchangeuser")
        user_id = user.id
        self.assertEqual(user.email, "old@example.com")

        WebhookDelivery.query.delete()
        db.session.commit()
        mock_requests.reset_mock()

        self.client.get("/profile/edit")
        self.client.post("/profile/edit", data={
            "email": "new@example.com",
            "csrf_token": g.csrf_token
        })

        db.session.refresh(user)
        self.assertEqual(user.email, "old@example.com")
        self.assertEqual(user.unconfirmed_email, "new@example.com")

        WebhookDelivery.query.delete()
        db.session.commit()
        mock_requests.reset_mock()

        timestamp = int(datetime.now().timestamp())
        checksum = create_email_link_checksum(VERIFY_EMAIL, user.id, "new@example.com", timestamp)
        verification_link = url_for(
            "users.verify_email",
            user_id=user.id,
            timestamp=timestamp,
            checksum=checksum,
            _external=True
        )
        response = self.client.get(verification_link)
        self.assertEqual(response.status_code, 302)

        deliveries = WebhookDelivery.query.filter_by(
            webhook_id=webhook.id,
            event_type=EVENT_USER_UPDATED
        ).all()

        self.assertEqual(len(deliveries), 1)
        delivery = deliveries[0]

        self.assertEqual(delivery.payload["user_id"], user_id)
        self.assertEqual(delivery.payload["old"]["email"], "old@example.com")
        self.assertEqual(delivery.payload["new"]["email"], "new@example.com")

        self.assertEqual(len(mock_requests.request_history), 1)
        self.assertEqual(delivery.status, "delivered")

    @requests_mock.Mocker()
    def test_admin_verify_email_triggers_webhook(self, mock_requests):
        """Test that admin email verification triggers webhook with correct payload."""
        self.app.config["ADMINS"] = ["adminuser"]
        admin_user = User.add(
            name="adminuser",
            unconfirmed_email="admin@example.com",
            password="adminpassword123"
        )
        db.session.commit()
        self.temporary_login(admin_user)

        webhook = Webhook(
            name="User Updated Webhook",
            url="https://example.com/webhooks/user-events",
            secret="mebw_secret_key",
            events=[EVENT_USER_UPDATED],
            is_active=True
        )
        db.session.add(webhook)
        db.session.commit()

        mock_requests.post(
            "https://example.com/webhooks/user-events",
            status_code=200,
            text='{"received": true}'
        )

        regular_user = User.add(
            name="regularuser",
            unconfirmed_email="unverified@example.com",
            password="password123"
        )
        db.session.commit()
        user_id = regular_user.id

        response = self.client.get(url_for("users-admin.details_view", id=user_id))
        self.assertEqual(response.status_code, 200)

        verify_email_form = self.get_context_variable("verify_email_form")

        response = self.client.post(
            url_for("users-admin.verify_user_email", user_id=user_id),
            data={"csrf_token": verify_email_form.csrf_token.current_token},
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 302)

        deliveries = WebhookDelivery.query.filter_by(
            webhook_id=webhook.id,
            event_type=EVENT_USER_UPDATED
        ).all()

        self.assertEqual(len(deliveries), 1)
        delivery = deliveries[0]

        self.assertEqual(delivery.payload["user_id"], user_id)
        self.assertIsNone(delivery.payload["old"]["email"])
        self.assertEqual(delivery.payload["new"]["email"], "unverified@example.com")

        self.assertEqual(len(mock_requests.request_history), 1)
        request = mock_requests.last_request
        self.assertEqual(request.headers["X-MetaBrainz-Event"], EVENT_USER_UPDATED)
        self.assertEqual(delivery.status, "delivered")

    @requests_mock.Mocker()
    def test_admin_edit_username_triggers_webhook(self, mock_requests):
        """Test that admin username edit triggers webhook with correct payload."""
        self.app.config["ADMINS"] = ["adminuser"]
        admin_user = User.add(
            name="adminuser",
            unconfirmed_email="admin@example.com",
            password="adminpassword123"
        )
        db.session.commit()
        self.temporary_login(admin_user)

        webhook = Webhook(
            name="User Updated Webhook",
            url="https://example.com/webhooks/user-events",
            secret="mebw_secret_key",
            events=[EVENT_USER_UPDATED],
            is_active=True
        )
        db.session.add(webhook)
        db.session.commit()

        mock_requests.post(
            "https://example.com/webhooks/user-events",
            status_code=200,
            text='{"received": true}'
        )

        regular_user = User.add(
            name="oldusername",
            unconfirmed_email="user@example.com",
            password="password123"
        )
        db.session.commit()
        user_id = regular_user.id

        response = self.client.get(url_for("users-admin.details_view", id=user_id))
        self.assertEqual(response.status_code, 200)

        edit_username_form = self.get_context_variable("edit_username_form")

        response = self.client.post(
            url_for("users-admin.edit_username", user_id=user_id),
            data={
                "username": "newusername",
                "csrf_token": edit_username_form.csrf_token.current_token,
            },
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 302)

        deliveries = WebhookDelivery.query.filter_by(
            webhook_id=webhook.id,
            event_type=EVENT_USER_UPDATED
        ).all()

        self.assertEqual(len(deliveries), 1)
        delivery = deliveries[0]

        self.assertEqual(delivery.payload["user_id"], user_id)
        self.assertEqual(delivery.payload["old"]["name"], "oldusername")
        self.assertEqual(delivery.payload["new"]["name"], "newusername")

        self.assertEqual(len(mock_requests.request_history), 1)
        request = mock_requests.last_request
        self.assertEqual(request.headers["X-MetaBrainz-Event"], EVENT_USER_UPDATED)
        self.assertEqual(delivery.status, "delivered")

    @requests_mock.Mocker()
    def test_admin_delete_user_triggers_webhook(self, mock_requests):
        """Test that admin user deletion triggers webhook with correct payload."""
        self.app.config["ADMINS"] = ["adminuser"]
        admin_user = User.add(
            name="adminuser",
            unconfirmed_email="admin@example.com",
            password="adminpassword123"
        )
        db.session.commit()
        self.temporary_login(admin_user)

        webhook = Webhook(
            name="User Deleted Webhook",
            url="https://example.com/webhooks/user-events",
            secret="mebw_secret_key",
            events=[EVENT_USER_DELETED],
            is_active=True
        )
        db.session.add(webhook)
        db.session.commit()

        mock_requests.post(
            "https://example.com/webhooks/user-events",
            status_code=200,
            text='{"received": true}'
        )

        regular_user = User.add(
            name="userToDelete",
            unconfirmed_email="todelete@example.com",
            password="password123"
        )
        db.session.commit()
        user_id = regular_user.id

        response = self.client.get(url_for("users-admin.details_view", id=user_id))
        self.assertEqual(response.status_code, 200)

        delete_form = self.get_context_variable("delete_user_form")

        response = self.client.post(
            url_for("users-admin.delete_user", user_id=user_id),
            data={
                "reason": "Test deletion by admin",
                "confirm": "y",
                "csrf_token": delete_form.csrf_token.current_token,
            },
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 302)

        deliveries = WebhookDelivery.query.filter_by(
            webhook_id=webhook.id,
            event_type=EVENT_USER_DELETED
        ).all()

        self.assertEqual(len(deliveries), 1)
        delivery = deliveries[0]

        self.assertEqual(delivery.payload["user_id"], user_id)
        self.assertEqual(delivery.payload["reason"], "Test deletion by admin")
        self.assertEqual(delivery.payload["moderator_id"], admin_user.id)

        self.assertEqual(len(mock_requests.request_history), 1)
        request = mock_requests.last_request
        self.assertEqual(request.headers["X-MetaBrainz-Event"], EVENT_USER_DELETED)
        self.assertEqual(delivery.status, "delivered")
