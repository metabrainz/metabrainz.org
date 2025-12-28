from flask import url_for

from metabrainz.model import db
from metabrainz.model.user import User
from metabrainz.model.webhook import Webhook, EVENT_USER_CREATED, EVENT_USER_UPDATED
from metabrainz.testing import FlaskTestCase


class WebhookAdminTestCase(FlaskTestCase):

    def setUp(self):
        super().setUp()
        self.app.config["ADMINS"] = ["admin_user"]

        self.admin_user = User.add(
            name="admin_user",
            unconfirmed_email="admin@metabrainz.org",
            password="adminpassword123"
        )
        db.session.commit()
        self.temporary_login(self.admin_user)

    def test_webhook_admin_index_requires_auth(self):
        """Test that webhook admin index requires authentication."""
        response = self.client.get(url_for("webhooks-admin.index_view"))
        self.assertEqual(response.status_code, 200)
        self.client.get("/logout")
        response = self.client.get(url_for("webhooks-admin.index_view"))
        self.assertEqual(response.status_code, 302)

    def test_create_webhook_with_auto_generated_secret(self):
        """Test creating a webhook auto-generates and flashes the secret."""
        self.client.get(url_for("webhooks-admin.create_view"))
        csrf_token = self.get_context_variable("form").csrf_token.current_token

        response = self.client.post(
            url_for("webhooks-admin.create_view"),
            data={
                "name": "Test Webhook",
                "url": "https://example.com/webhook",
                "events": [EVENT_USER_CREATED, EVENT_USER_UPDATED],
                "is_active": True,
                "csrf_token": csrf_token
            },
            follow_redirects=True
        )

        self.assertEqual(response.status_code, 200)

        webhook = Webhook.query.filter_by(name="Test Webhook").first()
        self.assertIsNotNone(webhook)
        self.assertEqual(webhook.url, "https://example.com/webhook")
        self.assertIn(EVENT_USER_CREATED, webhook.events)
        self.assertIn(EVENT_USER_UPDATED, webhook.events)
        self.assertTrue(webhook.is_active)

        self.assertIsNotNone(webhook.secret)
        self.assertTrue(webhook.secret.startswith("mebw_"))
        self.assertTrue(len(self.flashed_messages), 1)
        message, category = self.flashed_messages[0]
        self.assertIn("Webhook created successfully!", message)
        self.assertIn(webhook.secret, message)
        self.assertEqual(category, "success")

    def test_create_webhook_with_http(self):
        """Test that http:// URLs are only allowed for localhost in debug mode."""
        # Enable debug mode to allow localhost URLs
        self.app.config["DEBUG"] = True

        self.client.get(url_for("webhooks-admin.create_view"))
        csrf_token = self.get_context_variable("form").csrf_token.current_token

        response = self.client.post(
            url_for("webhooks-admin.create_view"),
            data={
                "name": "Localhost Webhook",
                "url": "http://localhost:8000/webhook",
                "events": [EVENT_USER_CREATED],
                "is_active": True,
                "csrf_token": csrf_token
            },
            follow_redirects=True
        )

        self.assertEqual(response.status_code, 200)
        webhook = Webhook.query.filter_by(name="Localhost Webhook").first()
        self.assertIsNotNone(webhook)
        self.assertEqual(webhook.url, "http://localhost:8000/webhook")

        self.client.get(url_for("webhooks-admin.create_view"))
        csrf_token = self.get_context_variable("form").csrf_token.current_token

        response = self.client.post(
            url_for("webhooks-admin.create_view"),
            data={
                "name": "Insecure Webhook",
                "url": "http://example.com/webhook",
                "events": [EVENT_USER_CREATED],
                "is_active": True,
                "csrf_token": csrf_token
            },
            follow_redirects=False
        )

        self.assertEqual(response.status_code, 200)
        webhook = Webhook.query.filter_by(name="Insecure Webhook").first()
        self.assertIsNone(webhook)

        # Disable debug mode
        self.app.config["DEBUG"] = False

    def test_create_webhook_with_localhost_blocked_in_production(self):
        """Test that localhost URLs are blocked when DEBUG is False."""
        # Ensure debug mode is disabled
        self.app.config["DEBUG"] = False

        self.client.get(url_for("webhooks-admin.create_view"))
        csrf_token = self.get_context_variable("form").csrf_token.current_token

        # Try to create webhook with localhost URL
        response = self.client.post(
            url_for("webhooks-admin.create_view"),
            data={
                "name": "Blocked Localhost Webhook",
                "url": "http://localhost:8000/webhook",
                "events": [EVENT_USER_CREATED],
                "is_active": True,
                "csrf_token": csrf_token
            },
            follow_redirects=False
        )

        self.assertEqual(response.status_code, 200)
        webhook = Webhook.query.filter_by(name="Blocked Localhost Webhook").first()
        self.assertIsNone(webhook)

        # Try with https localhost URL
        self.client.get(url_for("webhooks-admin.create_view"))
        csrf_token = self.get_context_variable("form").csrf_token.current_token

        response = self.client.post(
            url_for("webhooks-admin.create_view"),
            data={
                "name": "Blocked HTTPS Localhost Webhook",
                "url": "https://localhost:8000/webhook",
                "events": [EVENT_USER_CREATED],
                "is_active": True,
                "csrf_token": csrf_token
            },
            follow_redirects=False
        )

        self.assertEqual(response.status_code, 200)
        webhook = Webhook.query.filter_by(name="Blocked HTTPS Localhost Webhook").first()
        self.assertIsNone(webhook)

        # Try with private IP
        self.client.get(url_for("webhooks-admin.create_view"))
        csrf_token = self.get_context_variable("form").csrf_token.current_token

        response = self.client.post(
            url_for("webhooks-admin.create_view"),
            data={
                "name": "Blocked Private IP Webhook",
                "url": "https://192.168.1.100/webhook",
                "events": [EVENT_USER_CREATED],
                "is_active": True,
                "csrf_token": csrf_token
            },
            follow_redirects=False
        )

        self.assertEqual(response.status_code, 200)
        webhook = Webhook.query.filter_by(name="Blocked Private IP Webhook").first()
        self.assertIsNone(webhook)

    def test_create_webhook_without_events_fails(self):
        """Test that creating a webhook without events fails validation."""
        self.client.get(url_for("webhooks-admin.create_view"))
        csrf_token = self.get_context_variable("form").csrf_token.current_token

        response = self.client.post(
            url_for("webhooks-admin.create_view"),
            data={
                "name": "No Events Webhook",
                "url": "https://example.com/webhook",
                "events": [],
                "is_active": True,
                "csrf_token": csrf_token
            },
            follow_redirects=False
        )

        self.assertEqual(response.status_code, 200)
        webhook = Webhook.query.filter_by(name="No Events Webhook").first()
        self.assertIsNone(webhook)

    def test_create_webhook_without_url_fails(self):
        """Test that creating a webhook without URL fails validation."""
        self.client.get(url_for("webhooks-admin.create_view"))
        csrf_token = self.get_context_variable("form").csrf_token.current_token

        response = self.client.post(
            url_for("webhooks-admin.create_view"),
            data={
                "name": "No URL Webhook",
                "url": "",
                "events": [EVENT_USER_CREATED],
                "is_active": True,
                "csrf_token": csrf_token
            },
            follow_redirects=False
        )

        self.assertEqual(response.status_code, 200)
        webhook = Webhook.query.filter_by(name="No URL Webhook").first()
        self.assertIsNone(webhook)

    def test_create_webhook_with_invalid_url_protocol_fails(self):
        """Test that invalid URL protocols are rejected."""
        self.client.get(url_for("webhooks-admin.create_view"))
        csrf_token = self.get_context_variable("form").csrf_token.current_token

        response = self.client.post(
            url_for("webhooks-admin.create_view"),
            data={
                "name": "Invalid Protocol Webhook",
                "url": "javascript:alert('xss')",
                "events": [EVENT_USER_CREATED],
                "is_active": True,
                "csrf_token": csrf_token
            },
            follow_redirects=False
        )

        self.assertEqual(response.status_code, 200)

        webhook = Webhook.query.filter_by(name="Invalid Protocol Webhook").first()
        self.assertIsNone(webhook)

    def test_edit_webhook_preserves_secret(self):
        """Test that editing a webhook preserves the secret."""
        original_secret = "mebw_original_secret_12345"
        webhook = Webhook(
            name="Original Webhook",
            url="https://example.com/original",
            secret=original_secret,
            events=[EVENT_USER_CREATED],
            is_active=True
        )
        db.session.add(webhook)
        db.session.commit()

        self.client.get(url_for("webhooks-admin.edit_view", id=webhook.id))
        csrf_token = self.get_context_variable("form").csrf_token.current_token

        response = self.client.post(
            url_for("webhooks-admin.edit_view", id=webhook.id),
            data={
                "name": "Updated Webhook",
                "url": "https://example.com/updated",
                "events": [EVENT_USER_CREATED, EVENT_USER_UPDATED],
                # absence of is_active field means set to inactive
                "csrf_token": csrf_token
            },
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)

        db.session.refresh(webhook)
        self.assertEqual(webhook.name, "Updated Webhook")
        self.assertEqual(webhook.url, "https://example.com/updated")
        self.assertFalse(webhook.is_active)
        self.assertIn(EVENT_USER_UPDATED, webhook.events)
        self.assertEqual(webhook.secret, original_secret)

    def test_create_webhook_with_multiple_events(self):
        """Test creating a webhook with multiple event selections."""
        self.client.get(url_for("webhooks-admin.create_view"))
        csrf_token = self.get_context_variable("form").csrf_token.current_token

        response = self.client.post(
            url_for("webhooks-admin.create_view"),
            data={
                "name": "Multi-Event Webhook",
                "url": "https://example.com/webhook",
                "events": [EVENT_USER_CREATED, EVENT_USER_UPDATED],
                "is_active": True,
                "csrf_token": csrf_token
            },
            follow_redirects=True
        )

        self.assertEqual(response.status_code, 200)

        webhook = Webhook.query.filter_by(name="Multi-Event Webhook").first()
        self.assertIsNotNone(webhook)
        self.assertEqual(len(webhook.events), 2)
        self.assertIn(EVENT_USER_CREATED, webhook.events)
        self.assertIn(EVENT_USER_UPDATED, webhook.events)
