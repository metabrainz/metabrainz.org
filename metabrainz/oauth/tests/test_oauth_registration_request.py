import base64
import json
import os
from datetime import datetime, timedelta, timezone
from threading import Barrier, Thread
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from flask import g
from flask_login import current_user
from freezegun import freeze_time

from metabrainz import bcrypt
from metabrainz.model import db, OAuth2AccessToken, OAuth2AuthorizationCode, OAuth2RefreshToken
from metabrainz.model.domain_blacklist import DomainBlacklist
from metabrainz.model.oauth.client import OAuth2ClientPrivilege
from metabrainz.model.user import User
from metabrainz.model.webhook import Webhook, EVENT_USER_CREATED, EVENT_USER_UPDATED
from metabrainz.model.webhook_delivery import WebhookDelivery
from metabrainz.oauth.tests import OAuthTestCase


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
            ["seeded-user <seeded.user@example.com>"],
        )
        email_text = send_mail.call_args.kwargs["text"]
        normalized_email_text = " ".join(email_text.split())
        self.assertIn("This link expires in 7 days.", normalized_email_text)
        self.assertIn(
            "created for you by this OAuth client: Name: test-client",
            normalized_email_text,
        )
        self.assertIn(
            f"Client ID: {application['client_id']}",
            normalized_email_text,
        )
        self.assertIn(
            "Description: test-description",
            normalized_email_text,
        )
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
        self.assertIn(
            f"Client ID: {application['client_id']}",
            normalized_email_text,
        )
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
            with self.assertRaisesRegex(RuntimeError, "SMTP unavailable"):
                self._create_registration_request(application, scope="profile")

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

        response = self._create_registration_request(application, email_confirmed=True)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json["email_confirmed"])
        password_link = self.get_context_variable("password_link")

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

    def test_welcome_link_is_consumed_atomically(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        self._create_registration_request(application)
        password_link = self.get_context_variable("password_link")

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
                    "This account does not have a password yet. Please check your inbox "
                    "for the welcome email or contact support."
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
        deliveries = WebhookDelivery.query.filter_by(webhook_id=webhook.id).all()
        return {delivery.event_type: delivery.payload for delivery in deliveries}

    def test_registration_request_emits_user_updated_for_confirmed_email(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        webhook = self._subscribe_webhook()

        with patch("metabrainz.webhooks.tasks.publish_new_webhook_delivery"):
            response = self._create_registration_request(application, email_confirmed=True)

        self.assertEqual(response.status_code, 201)
        user = User.get(name="seeded-user")

        # user.created carries no address, so subscribers only hear about the
        # confirmed email if user.updated is emitted here: nothing is left for the
        # user to confirm that would emit it later
        events = self._delivered_events(webhook)
        self.assertCountEqual(events, [EVENT_USER_CREATED, EVENT_USER_UPDATED])
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
        # the address is still unconfirmed, the flow that confirms it emits the event
        self.assertCountEqual(self._delivered_events(webhook), [EVENT_USER_CREATED])

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
