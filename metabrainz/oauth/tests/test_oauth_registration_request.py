import base64
import hashlib
import json
import os
from urllib.parse import parse_qs, urlparse

from brainzutils import cache
from flask import g

from metabrainz.model import OAuth2AuthorizationCode, OAuth2Client, db
from metabrainz.model.oauth.client import OAuth2ClientPrivilege
from metabrainz.model.domain_blacklist import DomainBlacklist
from metabrainz.model.user import User
from metabrainz.oauth.registration_request import REGISTRATION_REQUEST_NAMESPACE
from metabrainz.oauth.tests import OAuthTestCase


class OAuthRegistrationRequestTestCase(OAuthTestCase):

    def setUp(self):
        self._authlib_insecure_transport = os.environ.get("AUTHLIB_INSECURE_TRANSPORT")
        os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "1"
        super().setUp()
        cache._r.flushall()

    def tearDown(self):
        cache._r.flushall()
        if self._authlib_insecure_transport is None:
            os.environ.pop("AUTHLIB_INSECURE_TRANSPORT", None)
        else:
            os.environ["AUTHLIB_INSECURE_TRANSPORT"] = self._authlib_insecure_transport
        super().tearDown()

    def _pkce_pair(self):
        code_verifier = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~"
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
        return code_verifier, code_challenge

    def _create_registration_request(self, application, **overrides):
        _code_verifier, code_challenge = self._pkce_pair()
        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "redirect_uri": "https://example.com/callback",
            "scope": "profile",
            "state": "random-state",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "username": "seeded-user",
            "email": "Seeded.User@example.com",
        }
        data.update(overrides)
        data = {
            key: value
            for key, value in data.items()
            if value is not None
        }
        return self.client.post("/oauth2/registration-requests", data=data)

    def _allow_registration_request_client(self, application):
        self.grant_privileges(application, OAuth2ClientPrivilege.REGISTRATION_REQUEST)

    def _assert_redirects_to_signup(self, redirect_to):
        response = self.client.get(redirect_to)
        self.assertEqual(response.status_code, 302)
        parsed = urlparse(response.location)
        self.assertEqual(parsed.path, "/signup")

        query = parse_qs(parsed.query)
        self.assertIn("next", query)
        self.assertIn("registration_request", query)
        self.assertTrue(query["next"][0].startswith("/oauth2/registration-requests/"))
        return response.location

    def _continue_to_authorize(self, continue_url):
        response = self.client.get(continue_url)
        self.assertEqual(response.status_code, 302)
        parsed = urlparse(response.location)
        self.assertEqual(parsed.path, "/oauth2/authorize")
        return response.location

    def _confirm_authorization(self, authorize_url, user_id):
        response = self.client.get(authorize_url)
        self.assertTemplateUsed("oauth/prompt.html")
        props = self.get_context_variable("props")
        self.assertIn("test-client", props)

        parsed = urlparse(authorize_url)
        query_string = {
            key: values[0]
            for key, values in parse_qs(parsed.query).items()
        }
        response = self.client.post("/oauth2/authorize/confirm", query_string=query_string, data={
            "confirm": "yes",
            "csrf_token": g.csrf_token,
        })
        self.assertEqual(response.status_code, 302)

        parsed = urlparse(response.location)
        query_args = parse_qs(parsed.query)
        self.assertIsNone(query_args.get("error"))
        self.assertEqual(query_args["state"], ["random-state"])
        self.assertEqual(len(query_args["code"]), 1)

        code = db.session.query(OAuth2AuthorizationCode).join(OAuth2Client).filter(
            OAuth2Client.client_id == query_string["client_id"],
            OAuth2AuthorizationCode.client_id == OAuth2Client.id,
            OAuth2AuthorizationCode.user_id == user_id,
        ).first()
        self.assertIsNotNone(code)
        self.assertEqual(code.code, query_args["code"][0])
        return query_args["code"][0]

    def test_registration_request_signup_chains_to_pkce_authorization(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        code_verifier, code_challenge = self._pkce_pair()

        response = self._create_registration_request(application, code_challenge=code_challenge)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["expires_in"], 300)
        self.assertTrue(response.json["request_id"].startswith("mebrq_"))
        self.assertEqual(response.headers["Location"], response.json["redirect_to"])
        cached_request = cache.get(response.json["request_id"], namespace=REGISTRATION_REQUEST_NAMESPACE)
        self.assertEqual(cached_request["username"], "seeded-user")
        self.assertEqual(cached_request["email"], "seeded.user@example.com")
        self.assertEqual(cached_request["client_name"], "test-client")
        self.assertEqual(cached_request["scope"], "profile")
        self.assertNotIn("authorize_params", cached_request)
        self.assertNotIn("client", cached_request)
        self.assertNotIn("hints", cached_request)

        signup_url = self._assert_redirects_to_signup(response.json["redirect_to"])
        self.client.get(signup_url)
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["initial_form_data"]["username"], "seeded-user")
        self.assertEqual(props["initial_form_data"]["email"], "seeded.user@example.com")
        self.assertTrue(props["is_registration_request_signup"])
        self.assertEqual(props["registration_request_client_name"], "test-client")

        response = self.client.post(signup_url, data={
            "username": "changed-user",
            "email": "changed@example.com",
            "password": "<PASSWORD>",
            "confirm_password": "<PASSWORD>",
            "agreement": "y",
            "csrf_token": g.csrf_token,
        })
        self.assertEqual(response.status_code, 302)
        user = User.get(name="seeded-user")
        self.assertIsNotNone(user)
        self.assertIsNone(User.get(name="changed-user"))

        authorize_url = self._continue_to_authorize(response.location)
        code = self._confirm_authorization(authorize_url, user.id)

        token = self.client.post("/oauth2/token", data={
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "authorization_code",
            "redirect_uri": "https://example.com/callback",
            "code_verifier": code_verifier,
            "code": code,
        })
        self.assert200(token)
        self.assertEqual(token.json["token_type"], "Bearer")
        self.assertIn("access_token", token.json)
        self.assertIn("refresh_token", token.json)

    def test_registration_request_logged_in_user_chains_to_authorization(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        response = self._create_registration_request(application, username="seeded-login-user")
        self.assertEqual(response.status_code, 201)

        self.temporary_login(self.user2)
        authorize_url = self._continue_to_authorize(response.json["redirect_to"])
        replay = self.client.get(response.json["redirect_to"])
        self.assertEqual(replay.status_code, 400)
        self._confirm_authorization(authorize_url, self.user2.id)

    def test_registration_request_signup_sign_in_link_chains_to_authorization(self):
        user = User.add(
            name="existing-user",
            unconfirmed_email="existing-user@example.com",
            password="<PASSWORD>",
        )
        db.session.commit()

        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        response = self._create_registration_request(application, username="seeded-login-user")
        self.assertEqual(response.status_code, 201)

        signup_url = self._assert_redirects_to_signup(response.json["redirect_to"])
        self.client.get(signup_url)
        props = json.loads(self.get_context_variable("props"))
        self.assertTrue(props["is_registration_request_signup"])

        parsed_signup = urlparse(signup_url)
        login_url = f"/login?{parsed_signup.query}"
        response = self.client.get(login_url)
        self.assertEqual(response.status_code, 200)
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["initial_form_data"]["username"], "seeded-login-user")

        response = self.client.post(login_url, data={
            "username": "existing-user",
            "password": "<PASSWORD>",
            "csrf_token": g.csrf_token,
        })
        self.assertEqual(response.status_code, 302)

        authorize_url = self._continue_to_authorize(response.location)
        self._confirm_authorization(authorize_url, user.id)

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

    def test_registration_request_rejects_invalid_redirect_uri(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        response = self._create_registration_request(
            application,
            redirect_uri="https://attacker.example/callback",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_request")

    def test_registration_request_rejects_invalid_scope(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        response = self._create_registration_request(application, scope="profile unknown")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_scope")

    def test_registration_request_rejects_missing_hints(self):
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

    def test_registration_request_rejects_unusable_hints(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        response = self._create_registration_request(application, username="test-user-2")
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

    def test_registration_request_rejects_invalid_authorization_request(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)

        response = self._create_registration_request(application, response_mode="invalid")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_request")

        response = self._create_registration_request(application, scope="openid profile")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "invalid_request")

    def test_registration_request_expired(self):
        application = self.create_oauth_app()
        self._allow_registration_request_client(application)
        response = self._create_registration_request(application)
        request_id = response.json["request_id"]
        cache.delete(request_id, namespace=REGISTRATION_REQUEST_NAMESPACE)

        response = self.client.get(response.json["redirect_to"])
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed("oauth/error.html")
