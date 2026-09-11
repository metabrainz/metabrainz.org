import base64
import json
import os
from datetime import datetime, timedelta, timezone
from threading import Barrier, Thread
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from brainzutils import cache
from flask import g
from flask_login import current_user
from freezegun import freeze_time
from sqlalchemy import delete, func

from metabrainz import bcrypt
from metabrainz.model import db, OAuth2AccessToken, OAuth2AuthorizationCode, OAuth2RefreshToken
from metabrainz.model.domain_blacklist import DomainBlacklist
from metabrainz.model.moderation_log import ModerationLog
from metabrainz.model.oauth.client import OAuth2Client, OAuth2ClientPrivilege
from metabrainz.model.oauth.provisioned_user import OAuth2ProvisionedUser
from metabrainz.model.user import User
from metabrainz.model.webhook import Webhook, EVENT_USER_CREATED, EVENT_USER_UPDATED
from metabrainz.model.webhook_delivery import WebhookDelivery
from metabrainz.oauth.tests import OAuthTestCase
from metabrainz.user.email import send_forgot_password_email
from metabrainz.user.registration import validate_registration_username


class OAuthRegistrationRequestTestCase(OAuthTestCase):

    def setUp(self):
        self._authlib_insecure_transport = os.environ.get("AUTHLIB_INSECURE_TRANSPORT")
        os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "1"
        super().setUp()

    def tearDown(self):
        if self._authlib_insecure_transport is None:
            os.environ.pop("AUTHLIB_INSECURE_TRANSPORT", None)
        else:
            os.environ["AUTHLIB_INSECURE_TRANSPORT"] = self._authlib_insecure_transport
        db.session.rollback()
        db.session.execute(delete(ModerationLog))
        db.session.commit()
        cache._r.flushall()
        super().tearDown()

    def _create_registration_request(self, application, **overrides):
        client_secret = overrides.pop("client_secret", application["client_secret"])
        data = {
            "username": "seeded-user",
            "email": "Seeded.User@example.com",
        }
        data.update(overrides)
        data = {
            key: value
            for key, value in data.items()
            if value is not None
        }
        credentials = base64.b64encode(
            f"{application['client_id']}:{client_secret}".encode()
        ).decode()
        return self.client.post(
            "/oauth2/registration-requests",
            json=data,
            headers={"Authorization": f"Basic {credentials}"},
        )

    def _allow_registration_request_client(self, application):
        self.grant_privileges(application, OAuth2ClientPrivilege.REGISTRATION_REQUEST)

    def test_registration_request_provisions_user_and_sends_welcome_email(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        with patch("metabrainz.user.email.send_mail") as send_mail:
            response = self._create_registration_request(application)

        self.assertEqual(response.status_code, 201)
        user = User.get(name="seeded-user")
        self.assertEqual(response.json, {
            "user_id": user.id,
            "username": "seeded-user",
            "email": "seeded.user@example.com",
            "email_confirmed": False,
        })
        self.assertEqual(user.password, "")
        self.assertIsNone(user.email)
        self.assertEqual(user.unconfirmed_email, "seeded.user@example.com")
        self.assertNotIn("Location", response.headers)
        self.assert_security_headers(response)

        send_mail.assert_called_once()
        self.assertEqual(send_mail.call_args.kwargs["subject"], "Welcome to MetaBrainz")
        self.assertEqual(
            send_mail.call_args.kwargs["recipients"],
            ["seeded.user@example.com"],
        )
        email_text = send_mail.call_args.kwargs["text"]
        normalized_email_text = " ".join(email_text.split())
        self.assertIn("This link expires in 7 days.", normalized_email_text)
        self.assertIn(
            "created for you by this OAuth client: Name: test-client",
            normalized_email_text,
        )
        self.assertIn(
            "Description: test-description",
            normalized_email_text,
        )
        self.assertNotIn(application["client_id"], normalized_email_text)
        self.assertIn(
            "No OAuth scopes were granted to this client.",
            normalized_email_text,
        )
        self.assertIn(
            'If you did not give "test-client" permission to create this account',
            normalized_email_text,
        )
        password_link = self.get_context_variable("password_link")
        parsed_password_link = urlparse(password_link)
        self.assertEqual(parsed_password_link.path, "/reset-password")
        self.assertEqual(parse_qs(parsed_password_link.query)["initial_setup"], ["1"])
        self.assertEqual(db.session.query(OAuth2AuthorizationCode).count(), 0)
        self.assertEqual(db.session.query(OAuth2AccessToken).count(), 0)
        self.assertEqual(db.session.query(OAuth2RefreshToken).count(), 0)

    def test_registration_request_accepts_json_with_basic_authentication(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        credentials = base64.b64encode(
            f"{application['client_id']}:{application['client_secret']}".encode()
        ).decode()

        response = self.client.post(
            "/oauth2/registration-requests",
            json={
                "username": "json-user",
                "email": "JSON.User@example.com",
                "email_confirmed": True,
            },
            headers={"Authorization": f"Basic {credentials}"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["username"], "json-user")
        self.assertEqual(response.json["email"], "json.user@example.com")
        self.assertTrue(response.json["email_confirmed"])
        user = User.get(name="json-user")
        self.assertEqual(user.password, "")
        self.assertEqual(user.email, "json.user@example.com")
        self.assertIsNone(user.unconfirmed_email)
        self.assertIsNotNone(user.email_confirmed_at)

    def test_registration_request_issues_tokens_for_requested_scopes(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        with patch("metabrainz.user.email.send_mail") as send_mail:
            response = self._create_registration_request(application, scope="profile email")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["token_type"], "Bearer")
        self.assertEqual(response.json["scope"], "profile email")
        self.assertIn("access_token", response.json)
        self.assertIn("refresh_token", response.json)
        self.assertGreater(response.json["expires_in"], 0)

        user = User.get(name="seeded-user")
        access_token = db.session.query(OAuth2AccessToken).filter_by(
            access_token=response.json["access_token"],
        ).one()
        refresh_token = db.session.query(OAuth2RefreshToken).filter_by(
            refresh_token=response.json["refresh_token"],
        ).one()
        self.assertEqual(access_token.user_id, user.id)
        self.assertEqual(refresh_token.user_id, user.id)
        self.assertEqual(
            {scope.name for scope in access_token.scopes},
            {"profile", "email"},
        )
        self.assertEqual(
            {scope.name for scope in refresh_token.scopes},
            {"profile", "email"},
        )
        self.assertEqual(db.session.query(OAuth2AuthorizationCode).count(), 0)

        send_mail.assert_called_once()
        normalized_email_text = " ".join(send_mail.call_args.kwargs["text"].split())
        self.assertIn("Name: test-client", normalized_email_text)
        self.assertNotIn(application["client_id"], normalized_email_text)
        self.assertIn("Description: test-description", normalized_email_text)
        self.assertIn(
            "The following OAuth scopes were granted to this client:",
            normalized_email_text,
        )
        self.assertIn(
            "- profile: View your public account information",
            normalized_email_text,
        )
        self.assertIn(
            "- email: View your email address",
            normalized_email_text,
        )
        self.assertNotIn(
            "No OAuth scopes were granted to this client.",
            normalized_email_text,
        )

        refreshed = self.client.post("/oauth2/token", data={
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": response.json["refresh_token"],
        })
        self.assert200(refreshed)
        self.assertCountEqual(refreshed.json["scope"], ["profile", "email"])

    def test_registration_request_allows_granted_restricted_scope(self):
        restricted_scope = "musicbrainz:submit_isrc"
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        self.restrict_scope(restricted_scope)
        self.grant_scopes(application, restricted_scope)

        response = self._create_registration_request(
            application,
            scope=f"profile {restricted_scope}",
        )

        self.assertEqual(response.status_code, 201)
        access_token = db.session.query(OAuth2AccessToken).filter_by(
            access_token=response.json["access_token"],
        ).one()
        self.assertEqual(
            {scope.name for scope in access_token.scopes},
            {"profile", restricted_scope},
        )

    def test_registration_request_rolls_back_when_welcome_email_fails(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        with patch(
            "metabrainz.oauth.views.send_welcome_email",
            side_effect=RuntimeError("SMTP unavailable"),
        ):
            response = self._create_registration_request(application, scope="profile")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json["error"], "server_error")
        self.assertEqual(
            response.json["error_description"],
            "The welcome email could not be sent, so the account was not created.",
        )
        self.assertIsNone(User.get(name="seeded-user"))
        self.assertIsNone(User.get(email="seeded.user@example.com"))
        self.assertEqual(db.session.query(OAuth2AccessToken).count(), 0)
        self.assertEqual(db.session.query(OAuth2RefreshToken).count(), 0)

        with patch("metabrainz.oauth.views.send_welcome_email"):
            response = self._create_registration_request(application, scope="profile")

        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(User.get(name="seeded-user"))

    def test_registration_request_trusts_confirmed_email_during_password_setup(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        with patch("metabrainz.user.email.send_mail") as send_mail:
            response = self._create_registration_request(application, email_confirmed=True)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json["email_confirmed"])

        send_mail.assert_called_once()
        self.assertEqual(send_mail.call_args.kwargs["subject"], "Welcome to MetaBrainz")
        self.assertEqual(
            send_mail.call_args.kwargs["recipients"],
            ["seeded.user@example.com"],
        )
        password_link = self.get_context_variable("password_link")
        self.assertIn(password_link, send_mail.call_args.kwargs["text"])

        user = User.get(name="seeded-user")
        confirmed_at = user.email_confirmed_at
        self.assertEqual(user.email, "seeded.user@example.com")
        self.assertIsNone(user.unconfirmed_email)
        self.assertIsNotNone(confirmed_at)

        self.client.get(password_link)
        response = self.client.post(password_link, data={
            "password": "<NEW-PASSWORD>",
            "confirm_password": "<NEW-PASSWORD>",
            "csrf_token": g.csrf_token,
        })

        self.assertRedirects(response, "/login")
        user = User.get(name="seeded-user")
        self.assertTrue(bcrypt.check_password_hash(user.password, "<NEW-PASSWORD>"))
        self.assertEqual(user.email, "seeded.user@example.com")
        self.assertIsNone(user.unconfirmed_email)
        self.assertEqual(user.email_confirmed_at, confirmed_at)

    def _assert_password_setup_preserves_pending_email(self, is_welcome_link):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        response = self._create_registration_request(application, email_confirmed=True)
        self.assertEqual(response.status_code, 201)
        password_link = self.get_context_variable("password_link")

        user = User.get(name="seeded-user")
        confirmed_at = user.email_confirmed_at
        if not is_welcome_link:
            send_forgot_password_email(user)
            password_link = self.get_context_variable("reset_password_link")

        user.change_email(self.user1, "pending@example.com", confirmed=False)
        db.session.commit()
        webhook = self._subscribe_webhook()

        response = self.client.get(password_link)
        self.assert200(response)
        with patch("metabrainz.webhooks.tasks.publish_new_webhook_delivery"):
            response = self.client.post(password_link, data={
                "password": "<NEW-PASSWORD>",
                "confirm_password": "<NEW-PASSWORD>",
                "csrf_token": g.csrf_token,
            })

        self.assertRedirects(response, "/login")
        db.session.expire_all()
        user = User.get(name="seeded-user")
        self.assertTrue(bcrypt.check_password_hash(user.password, "<NEW-PASSWORD>"))
        self.assertEqual(user.email, "seeded.user@example.com")
        self.assertEqual(user.unconfirmed_email, "pending@example.com")
        self.assertEqual(user.email_confirmed_at, confirmed_at)
        self.assertEqual(self._delivered_events(webhook), [])

    def test_welcome_link_does_not_confirm_a_different_pending_email(self):
        self._assert_password_setup_preserves_pending_email(is_welcome_link=True)

    def test_reset_link_does_not_confirm_a_different_pending_email_during_setup(self):
        self._assert_password_setup_preserves_pending_email(is_welcome_link=False)

    def test_welcome_link_sets_password_and_confirms_email(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        response = self._create_registration_request(application)
        self.assertEqual(response.status_code, 201)
        password_link = self.get_context_variable("password_link")

        response = self.client.get(password_link)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed("users/reset-password.html")
        props = json.loads(self.get_context_variable("props"))
        self.assertTrue(props["is_initial_setup"])

        response = self.client.post(password_link, data={
            "password": "<NEW-PASSWORD>",
            "confirm_password": "<NEW-PASSWORD>",
            "csrf_token": g.csrf_token,
        })
        self.assertRedirects(response, "/login")
        self.assertMessageFlashed("Password set! You can now sign in.", "success")

        user = User.get(name="seeded-user")
        self.assertTrue(bcrypt.check_password_hash(user.password, "<NEW-PASSWORD>"))
        self.assertEqual(user.email, "seeded.user@example.com")
        self.assertIsNone(user.unconfirmed_email)
        self.assertIsNotNone(user.email_confirmed_at)

        self.client.get("/login")
        response = self.client.post("/login", data={
            "username": "seeded-user",
            "password": "<NEW-PASSWORD>",
            "csrf_token": g.csrf_token,
        })
        self.assertRedirects(response, "/")
        self.assertEqual(current_user, user)

    def test_welcome_link_expires_after_seven_days(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        response = self._create_registration_request(application)
        self.assertEqual(response.status_code, 201)
        password_link = self.get_context_variable("password_link")

        with freeze_time(datetime.now(timezone.utc) + timedelta(days=7)):
            response = self.client.get(password_link)

        self.assertRedirects(response, "/")
        self.assertMessageFlashed("Set password link expired.", "error")
        self.assertEqual(User.get(name="seeded-user").password, "")

    def test_welcome_link_is_single_use(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        self._create_registration_request(application)
        password_link = self.get_context_variable("password_link")
        self.client.get(password_link)
        self.client.post(password_link, data={
            "password": "<NEW-PASSWORD>",
            "confirm_password": "<NEW-PASSWORD>",
            "csrf_token": g.csrf_token,
        })

        response = self.client.get(password_link)

        self.assertRedirects(response, "/")
        self.assertMessageFlashed("This account already has a password.", "error")

    def _assert_first_password_is_set_atomically(self, is_welcome_link):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        self._create_registration_request(application)
        password_link = self.get_context_variable("password_link")
        if not is_welcome_link:
            send_forgot_password_email(User.get(name="seeded-user"))
            password_link = self.get_context_variable("reset_password_link")

        original_hash = bcrypt.generate_password_hash
        hash_barrier = Barrier(2, timeout=10)
        responses = []
        errors = []

        def synchronized_hash(password):
            hash_barrier.wait()
            return original_hash(password)

        def submit_password(password):
            try:
                with self.app.test_client() as client:
                    response = client.post(password_link, data={
                        "password": password,
                        "confirm_password": password,
                    })
                    responses.append((response.status_code, urlparse(response.location).path))
            except Exception as error:
                errors.append(error)

        csrf_enabled = self.app.config.get("WTF_CSRF_ENABLED", True)
        self.app.config["WTF_CSRF_ENABLED"] = False
        try:
            with patch(
                "metabrainz.user.views.bcrypt.generate_password_hash",
                side_effect=synchronized_hash,
            ):
                threads = [
                    Thread(target=submit_password, args=("<FIRST-PASSWORD>",)),
                    Thread(target=submit_password, args=("<SECOND-PASSWORD>",)),
                ]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=20)
                self.assertTrue(all(not thread.is_alive() for thread in threads))
        finally:
            self.app.config["WTF_CSRF_ENABLED"] = csrf_enabled

        self.assertEqual(errors, [])
        self.assertCountEqual(responses, [(302, "/login"), (302, "/")])

        db.session.expire_all()
        user = User.get(name="seeded-user")
        self.assertTrue(
            bcrypt.check_password_hash(user.password, "<FIRST-PASSWORD>")
            or bcrypt.check_password_hash(user.password, "<SECOND-PASSWORD>")
        )

    def test_welcome_link_is_consumed_atomically(self):
        self._assert_first_password_is_set_atomically(is_welcome_link=True)

    def test_reset_link_setting_the_first_password_is_consumed_atomically(self):
        self._assert_first_password_is_set_atomically(is_welcome_link=False)

    def test_user_without_password_cannot_log_in(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        self._create_registration_request(application)

        self.client.get("/login")
        response = self.client.post("/login", data={
            "username": "seeded-user",
            "password": "<PASSWORD>",
            "csrf_token": g.csrf_token,
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(current_user.is_anonymous)
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(
            props["initial_errors"],
            {
                "password": (
                    "This account does not have a password set. Use the password reset "
                    "link to choose one, or contact support."
                )
            },
        )

    def test_registration_request_rejects_invalid_client_secret(self):
        application = self.create_oauth_app()
        response = self._create_registration_request(application, client_secret="wrong")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json["error"], "invalid_client")

    def test_registration_request_rejects_unauthorized_client(self):
        application = self.create_oauth_app()
        response = self._create_registration_request(application)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json["error"], "unauthorized_client")

    def test_registration_request_rejects_missing_user_details(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        response = self._create_registration_request(application, username=None)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_request")
        self.assertEqual(response.json["error_description"], "Missing 'username' in request.")

        response = self._create_registration_request(application, email=None)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_request")
        self.assertEqual(response.json["error_description"], "Missing 'email' in request.")

    def test_registration_request_rejects_non_string_user_details(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        response = self._create_registration_request(application, username=1)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_request")
        self.assertEqual(response.json["error_description"], "Invalid 'username' in request.")

        response = self._create_registration_request(application, email=["user@example.com"])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_request")
        self.assertEqual(response.json["error_description"], "Invalid 'email' in request.")

    def test_registration_request_rejects_invalid_email_confirmation(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        response = self._create_registration_request(application, email_confirmed="true")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_request")
        self.assertEqual(
            response.json["error_description"],
            "Invalid 'email_confirmed' in request; expected a boolean.",
        )

    def test_registration_request_rejects_non_string_scope(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        response = self._create_registration_request(application, scope=["profile"])

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_request")
        self.assertEqual(
            response.json["error_description"],
            "Invalid 'scope' in request; expected a space-separated string.",
        )
        self.assertIsNone(User.get(name="seeded-user"))

    def test_registration_request_rejects_unknown_scope(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        response = self._create_registration_request(application, scope="profile unknown")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_scope")
        self.assertIsNone(User.get(name="seeded-user"))

        response = self._create_registration_request(application, scope="   ")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_scope")
        self.assertIsNone(User.get(name="seeded-user"))

    def _subscribe_webhook(self):
        webhook = Webhook(
            name="User Events Webhook",
            url="https://example.com/webhooks/user-events",
            secret="mebw_secret",
            events=[EVENT_USER_CREATED, EVENT_USER_UPDATED],
            is_active=True,
        )
        db.session.add(webhook)
        db.session.commit()
        return webhook

    def _delivered_events(self, webhook):
        """Return (event_type, payload) pairs, preserving duplicate deliveries."""
        deliveries = (
            WebhookDelivery.query
            .filter_by(webhook_id=webhook.id)
            .order_by(WebhookDelivery.created_at)
            .all()
        )
        return [(delivery.event_type, delivery.payload) for delivery in deliveries]

    def _delivered_event_types(self, webhook):
        return [event_type for event_type, _ in self._delivered_events(webhook)]

    def test_registration_request_emits_user_updated_for_confirmed_email(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        webhook = self._subscribe_webhook()

        with patch("metabrainz.webhooks.tasks.publish_new_webhook_delivery"):
            response = self._create_registration_request(application, email_confirmed=True)

        self.assertEqual(response.status_code, 201)
        user = User.get(name="seeded-user")

        events = dict(self._delivered_events(webhook))
        self.assertEqual(
            self._delivered_event_types(webhook),
            [EVENT_USER_CREATED, EVENT_USER_UPDATED],
        )
        self.assertNotIn("email", events[EVENT_USER_CREATED])
        self.assertEqual(events[EVENT_USER_UPDATED], {
            "user_id": user.id,
            "old": {"email": None},
            "new": {"email": "seeded.user@example.com"},
            "updated_at": user.email_confirmed_at.isoformat(),
        })

    def test_registration_request_defers_user_updated_for_unconfirmed_email(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        webhook = self._subscribe_webhook()

        with patch("metabrainz.webhooks.tasks.publish_new_webhook_delivery"):
            response = self._create_registration_request(application)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(self._delivered_event_types(webhook), [EVENT_USER_CREATED])

    def test_registration_request_rejects_openid_scope(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        response = self._create_registration_request(application, scope="openid profile")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_scope")
        self.assertEqual(
            response.json["error_description"],
            "The 'openid' scope cannot be requested at this endpoint; it does not issue ID tokens.",
        )
        self.assertIsNone(User.get(name="seeded-user"))
        self.assertEqual(db.session.query(OAuth2AccessToken).count(), 0)
        self.assertEqual(db.session.query(OAuth2RefreshToken).count(), 0)

    def test_registration_request_rejects_email_taken_in_another_case(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        self.user2.email = "Seeded.User@example.com"
        db.session.commit()

        response = self._create_registration_request(application, email_confirmed=True)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_request")
        self.assertEqual(response.json["error_description"], "The requested email is already in use.")
        self.assertIsNone(User.get(name="seeded-user"))
        self.assertEqual(User.confirmed_email_exists("seeded.user@example.com"), True)
        self.assertEqual(
            db.session.query(User).filter(func.lower(User.email) == "seeded.user@example.com").count(),
            1,
        )

    def test_registration_request_rejects_ungranted_restricted_scope(self):
        restricted_scope = "musicbrainz:submit_isrc"
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        self.restrict_scope(restricted_scope)

        response = self._create_registration_request(
            application,
            scope=f"profile {restricted_scope}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_scope")
        self.assertEqual(
            response.json["error_description"],
            "The client is not allowed to request the following scopes: "
            + restricted_scope,
        )
        self.assertIsNone(User.get(name="seeded-user"))
        self.assertEqual(db.session.query(OAuth2AccessToken).count(), 0)
        self.assertEqual(db.session.query(OAuth2RefreshToken).count(), 0)

    def test_registration_request_rejects_form_encoded_body(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        credentials = base64.b64encode(
            f"{application['client_id']}:{application['client_secret']}".encode()
        ).decode()

        response = self.client.post(
            "/oauth2/registration-requests",
            data={
                "username": "form-user",
                "email": "form-user@example.com",
            },
            headers={"Authorization": f"Basic {credentials}"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_request")
        self.assertEqual(
            response.json["error_description"],
            "Request body must be a JSON object.",
        )

    def test_registration_request_rejects_credentials_in_json_body(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        response = self.client.post(
            "/oauth2/registration-requests",
            json={
                "client_id": application["client_id"],
                "client_secret": application["client_secret"],
                "username": "json-credentials-user",
                "email": "json-credentials-user@example.com",
            },
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json["error"], "invalid_client")

    def test_registration_request_handles_concurrent_username_conflicts(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        credentials = base64.b64encode(
            f"{application['client_id']}:{application['client_secret']}".encode()
        ).decode()
        validation_barrier = Barrier(2, timeout=10)
        responses = []
        errors = []

        def synchronized_validation(username):
            result = validate_registration_username(username)
            validation_barrier.wait()
            return result

        def provision_user(username, email):
            try:
                with self.app.test_client() as client:
                    response = client.post(
                        "/oauth2/registration-requests",
                        json={
                            "username": username,
                            "email": email,
                            "scope": "profile",
                        },
                        headers={"Authorization": f"Basic {credentials}"},
                    )
                    responses.append(response)
            except Exception as error:
                errors.append(error)

        with (
            patch(
                "metabrainz.oauth.views.validate_registration_username",
                side_effect=synchronized_validation,
            ),
            patch("metabrainz.oauth.views.send_welcome_email") as send_welcome_email,
        ):
            threads = [
                Thread(target=provision_user, args=(username, email))
                for username, email in (
                    ("seeded-user", "first@example.com"),
                    ("SEEDED-USER", "second@example.com"),
                )
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=20)
            self.assertTrue(all(not thread.is_alive() for thread in threads))

        self.assertEqual(errors, [])
        self.assertCountEqual([response.status_code for response in responses], [201, 400])
        conflict_response = next(response for response in responses if response.status_code == 400)
        self.assertEqual(conflict_response.json, {
            "error": "invalid_request",
            "error_description": "The requested username is already in use.",
        })
        send_welcome_email.assert_called_once()
        self.assertEqual(
            User.query.filter(func.lower(User.name) == "seeded-user").count(),
            1,
        )
        self.assertEqual(db.session.query(OAuth2AccessToken).count(), 1)
        self.assertEqual(db.session.query(OAuth2RefreshToken).count(), 1)

    def test_registration_request_reraises_unrelated_integrity_errors(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        existing_login_id = self.user1.login_id
        original_add = User.add

        def add_user_with_duplicate_login_id(**kwargs):
            user = original_add(**kwargs)
            user.login_id = existing_login_id
            return user

        with patch("metabrainz.oauth.views.User.add", side_effect=add_user_with_duplicate_login_id):
            response = self._create_registration_request(application, scope="profile")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json["error"], "server_error")
        self.assertIsNone(User.get(name="seeded-user"))
        self.assertEqual(db.session.query(OAuth2AccessToken).count(), 0)
        self.assertEqual(db.session.query(OAuth2RefreshToken).count(), 0)

    def test_registration_request_emits_nothing_when_the_welcome_email_fails(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        webhook = self._subscribe_webhook()

        with (
            patch("metabrainz.webhooks.tasks.publish_new_webhook_delivery"),
            patch(
                "metabrainz.oauth.views.send_welcome_email",
                side_effect=RuntimeError("SMTP unavailable"),
            ),
        ):
            response = self._create_registration_request(application, email_confirmed=True)

        # emit_event commits internally, so premature events can survive a failed request.
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self._delivered_events(webhook), [])
        self.assertIsNone(User.get(name="seeded-user"))

    def test_registration_request_emits_each_event_once(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        webhook = self._subscribe_webhook()

        with patch("metabrainz.webhooks.tasks.publish_new_webhook_delivery"):
            response = self._create_registration_request(application, email_confirmed=True)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            self._delivered_event_types(webhook),
            [EVENT_USER_CREATED, EVENT_USER_UPDATED],
        )

    def test_registration_request_records_the_provisioning_client(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        response = self._create_registration_request(application, scope="profile")

        self.assertEqual(response.status_code, 201)
        user = User.get(name="seeded-user")
        client = db.session.query(OAuth2Client).filter_by(
            client_id=application["client_id"],
        ).one()
        record = db.session.query(OAuth2ProvisionedUser).one()
        self.assertEqual(record.user_id, user.id)
        self.assertEqual(record.client_id, client.id)
        self.assertEqual(record.client.name, "test-client")
        self.assertIsNotNone(record.created_at)

    def test_registration_request_records_nothing_when_it_fails(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        with patch(
            "metabrainz.oauth.views.send_welcome_email",
            side_effect=RuntimeError("SMTP unavailable"),
        ):
            response = self._create_registration_request(application)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(db.session.query(OAuth2ProvisionedUser).count(), 0)

    def test_registration_request_answers_in_json_when_it_fails_unexpectedly(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        with patch(
            "metabrainz.oauth.views.check_registration_request_rate_limit",
            side_effect=RuntimeError("cache unavailable"),
        ):
            response = self._create_registration_request(application)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json["error"], "server_error")
        self.assertIsNone(User.get(name="seeded-user"))

    def test_registration_request_rejects_a_malformed_email(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        for email in ("bob@x.com\nbcc: victim@example.com", "a@", "not-an-address"):
            with self.subTest(email=email):
                response = self._create_registration_request(application, email=email)

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json["error"], "invalid_request")
                self.assertEqual(response.json["error_description"], "Invalid 'email' in request.")
                self.assertIsNone(User.get(name="seeded-user"))

    def test_registration_request_is_rate_limited_per_client(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        self.app.config["REGISTRATION_REQUEST_RATE_LIMIT_PER_CLIENT"] = 1
        try:
            first = self._create_registration_request(application, username="first-user")
            self.assertEqual(first.status_code, 201)

            second = self._create_registration_request(application, username="second-user")
        finally:
            del self.app.config["REGISTRATION_REQUEST_RATE_LIMIT_PER_CLIENT"]

        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.json["error"], "access_denied")
        self.assertIsNone(User.get(name="second-user"))

    def test_provisioned_token_does_not_stand_in_for_consent(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        response = self._create_registration_request(application, scope="profile")
        self.assertEqual(response.status_code, 201)

        access_token = db.session.query(OAuth2AccessToken).filter_by(
            access_token=response.json["access_token"],
        ).one()
        self.assertTrue(access_token.provisioned)

        user = User.get(name="seeded-user")
        user.password = bcrypt.generate_password_hash("<PASSWORD>").decode("utf-8")
        db.session.commit()
        self.temporary_login(user)

        authorize = self.client.get("/oauth2/authorize", query_string={
            "client_id": application["client_id"],
            "response_type": "code",
            "scope": "profile",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback",
        })

        self.assertEqual(authorize.status_code, 200)
        self.assertTemplateUsed("oauth/prompt.html")

    def test_refreshing_a_provisioned_token_does_not_launder_it_into_consent(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        response = self._create_registration_request(application, scope="profile")
        self.assertEqual(response.status_code, 201)

        refreshed = self.client.post("/oauth2/token", data={
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": response.json["refresh_token"],
        })
        self.assert200(refreshed)

        access_token = db.session.query(OAuth2AccessToken).filter_by(
            access_token=refreshed.json["access_token"],
        ).one()
        self.assertTrue(access_token.provisioned)

        user = User.get(name="seeded-user")
        user.password = bcrypt.generate_password_hash("<PASSWORD>").decode("utf-8")
        db.session.commit()
        self.temporary_login(user)

        authorize = self.client.get("/oauth2/authorize", query_string={
            "client_id": application["client_id"],
            "response_type": "code",
            "scope": "profile",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback",
        })

        self.assertEqual(authorize.status_code, 200)
        self.assertTemplateUsed("oauth/prompt.html")

    def test_welcome_link_ignores_the_request_host(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        credentials = base64.b64encode(
            f"{application['client_id']}:{application['client_secret']}".encode()
        ).decode()

        response = self.client.post(
            "/oauth2/registration-requests",
            json={"username": "seeded-user", "email": "seeded.user@example.com"},
            headers={
                "Authorization": f"Basic {credentials}",
                "Host": "evil.example",
            },
        )

        self.assertEqual(response.status_code, 201)
        password_link = self.get_context_variable("password_link")
        self.assertTrue(
            password_link.startswith(self.app.config["SERVER_BASE_URL"]),
            password_link,
        )
        self.assertNotIn("evil.example", password_link)

    def test_password_link_rejects_a_non_ascii_checksum(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        self._create_registration_request(application)
        user = User.get(name="seeded-user")

        # hmac.compare_digest raises for non-ASCII strings.
        response = self.client.get("/reset-password", query_string={
            "user_id": user.id,
            "ts": int(datetime.now(timezone.utc).timestamp()),
            "checksum": "\u00e9",
            "initial_setup": "1",
        })

        self.assertRedirects(response, "/")
        self.assertMessageFlashed("Unable to set password.", "error")

    def test_registration_request_handles_concurrent_email_conflicts(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        credentials = base64.b64encode(
            f"{application['client_id']}:{application['client_secret']}".encode()
        ).decode()
        validation_barrier = Barrier(2, timeout=10)
        responses = []
        errors = []

        def synchronized_validation(username):
            result = validate_registration_username(username)
            validation_barrier.wait()
            return result

        def provision_user(username):
            try:
                with self.app.test_client() as client:
                    responses.append(client.post(
                        "/oauth2/registration-requests",
                        json={
                            "username": username,
                            "email": "shared@example.com",
                            "scope": "profile",
                        },
                        headers={"Authorization": f"Basic {credentials}"},
                    ))
            except Exception as error:
                errors.append(error)

        with (
            patch(
                "metabrainz.oauth.views.validate_registration_username",
                side_effect=synchronized_validation,
            ),
            patch("metabrainz.oauth.views.send_welcome_email"),
        ):
            threads = [
                Thread(target=provision_user, args=(username,))
                for username in ("first-user", "second-user")
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=20)
            self.assertTrue(all(not thread.is_alive() for thread in threads))

        # Email addresses have no unique index, so provisioning must serialize on the address.
        self.assertEqual(errors, [])
        self.assertCountEqual([response.status_code for response in responses], [201, 400])
        conflict = next(response for response in responses if response.status_code == 400)
        self.assertEqual(conflict.json, {
            "error": "invalid_request",
            "error_description": "The requested email is already in use.",
        })
        self.assertEqual(
            User.query.filter(func.lower(User.unconfirmed_email) == "shared@example.com").count(),
            1,
        )

    def test_registration_request_rejects_unusable_user_details(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        response = self._create_registration_request(application, username="TEST-USER-2")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_request")
        self.assertEqual(response.json["error_description"], "The requested username is already in use.")

        self.user2.unconfirmed_email = "test-user-2@example.com"
        db.session.commit()
        response = self._create_registration_request(application, email="test-user-2@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_request")
        self.assertEqual(response.json["error_description"], "The requested email is already in use.")

        DomainBlacklist.add("spam.com", reason="Known spam domain")
        db.session.commit()
        response = self._create_registration_request(application, email="seeded-user@spam.com")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_request")
        self.assertEqual(
            response.json["error_description"],
            "Registration from this email domain is not allowed.",
        )
