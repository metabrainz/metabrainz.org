import base64
import json
from datetime import datetime, timedelta
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs, unquote, urlencode

import pytest
from flask import g
from freezegun import freeze_time
from werkzeug.datastructures import MultiDict

from oauth.authorization_code_grant import AuthorizationCodeGrant
from oauth.model import OAuth2AuthorizationCode, OAuth2Client, db, OAuth2AccessToken, OAuth2RefreshToken
from oauth.tests import login_user, OAuthTestCase


class AuthorizationCodeGrantTestCase(OAuthTestCase):

    def test_oauth_token_success(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        self.token_success_token_grant_helper(application, code, redirect_uri, True)

    def test_oauth_authorize_post_token_success(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        data = {
            "client_id": application["client_id"],
            "response_type": "code",
            "scope": "test-scope-1",
            "state": "random-state",
            "redirect_uri": redirect_uri,
        }
        with login_user(self.user2):
            response = self.client.post("/oauth2/authorize", data=data)
            self.assertTemplateUsed("oauth/prompt.html")
            props = json.loads(self.get_context_variable("props"))

            self.assertEqual(props["client_name"], "test-client")
            self.assertEqual(props["scopes"], [{"name": "test-scope-1", "description": "Test Scope 1"}])
            self.assertEqual(props["cancel_url"], redirect_uri + "?error=access_denied")
            self.assertEqual(props["csrf_token"], g.csrf_token)

            parsed = urlparse(props["submission_url"])
            self.assertEqual(parsed.path, "/oauth2/authorize/confirm")
            self.assertEqual(parse_qs(parsed.query), {k: [v] for k, v in data.items()})

            response = self.client.post("/oauth2/authorize/confirm", query_string=urlencode(data), data={
                "confirm": "yes",
                "csrf_token": g.csrf_token
            })
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.startswith(redirect_uri))
            parsed = urlparse(response.location)
            query_args = parse_qs(parsed.query)

            self.assertIsNone(query_args.get("error"))

            self.assertEqual(len(query_args["state"]), 1)
            self.assertEqual(query_args["state"][0], "random-state")

            self.assertEqual(len(query_args["code"]), 1)
            codes = db.session.query(OAuth2AuthorizationCode).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2AuthorizationCode.client_id == OAuth2Client.id,
                OAuth2AuthorizationCode.user_id == self.user2.id,
            ).all()
            codes = {code.code for code in codes}
            self.assertIn(query_args["code"][0], codes)

            self.assertEqual(parsed.fragment, "_")

            self.token_success_token_grant_helper(application, query_args["code"][0], redirect_uri, True)

    def _test_oauth_token_error_helper(self, data, error):
        with patch.object(AuthorizationCodeGrant, "authenticate_user", return_value=self.user2):
            response = self.client.post("/oauth2/token", data=data)
            # error code for invalid_client can be 400 or 401 depending on how validation failed
            if error["error"] == "invalid_client":
                self.assertIn(response.status_code, (400, 401))
            else:
                self.assert400(response)
            self.assertEqual(response.json, error)

    def test_oauth_token_invalid_client_id(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)

        data = {
            "client_id": "xxx",
            "client_secret": application["client_secret"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }
        error = {"error": "invalid_client"}
        self._test_oauth_token_error_helper(data, error)

    def test_oauth_token_no_client_id(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)

        data = {
            "client_secret": application["client_secret"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }
        error = {"error": "invalid_client"}
        self._test_oauth_token_error_helper(data, error)

    def test_oauth_token_no_client_secret(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }
        error = {"error": "invalid_client"}
        self._test_oauth_token_error_helper(data, error)

    def test_oauth_token_client_secret_mismatch(self):
        application1 = self.create_oauth_app()
        application2 = self.create_oauth_app()[1]
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application1, redirect_uri, True)

        data = {
            "client_id": application1["client_id"],
            "client_secret": application2["client_secret"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }
        error = {"error": "invalid_client"}
        self._test_oauth_token_error_helper(data, error)

        data = {
            "client_id": application2["client_id"],
            "client_secret": application1["client_secret"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }
        error = {"error": "invalid_client"}
        self._test_oauth_token_error_helper(data, error)

    def test_oauth_token_invalid_client_secret(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": "xxx",
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }
        error = {"error": "invalid_client"}
        self._test_oauth_token_error_helper(data, error)

    def test_oauth_token_invalid_grant_type(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "token",
            "redirect_uri": redirect_uri,
            "code": code,
        }
        error = {"error": "unsupported_grant_type"}
        self._test_oauth_token_error_helper(data, error)

    def test_oauth_token_missing_grant_type(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "redirect_uri": redirect_uri,
            "code": code,
        }
        error = {"error": "unsupported_grant_type"}
        self._test_oauth_token_error_helper(data, error)

    @pytest.mark.skip
    def test_oauth_token_parameter_reuse(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)

        data = MultiDict([
            ("client_id", application["client_id"]),
            ("client_secret", application["client_secret"]),
            ("redirect_uri", redirect_uri),
            ("grant_type", "code"),
            ("grant_type", "token"),
            ("code", code)
        ])
        error = {}
        self._test_oauth_token_error_helper(data, error)

    def test_oauth_token_missing_redirect_uri(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "authorization_code",
            "code": code,
        }
        error = {
            "error": "invalid_grant",
            "error_description": "Invalid \"redirect_uri\" in request."
        }
        self._test_oauth_token_error_helper(data, error)

    def test_oauth_token_invalid_redirect_uri(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri + "2",
            "code": code,
        }
        error = {
            "error": "invalid_grant",
            "error_description": "Invalid \"redirect_uri\" in request."
        }
        self._test_oauth_token_error_helper(data, error)

    def test_oauth_token_redirect_uri_mismatch(self):
        redirect_uri1 = "https://example.com/callback1"
        redirect_uri2 = "https://example.com/callback2"

        application = self.create_oauth_app(redirect_uris=[redirect_uri1, redirect_uri2])
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri1, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri2,
            "code": code,
        }
        error = {
            "error": "invalid_grant",
            "error_description": "Invalid \"redirect_uri\" in request."
        }
        self._test_oauth_token_error_helper(data, error)

    def test_oauth_token_invalid_code(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code + code,
        }
        error = {
            "error": "invalid_grant",
            "error_description": "Invalid \"code\" in request.",
        }
        self._test_oauth_token_error_helper(data, error)

    def test_oauth_token_missing_code(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        error = {
            "error": "invalid_request",
            "error_description": "Missing \"code\" in request."
        }
        self._test_oauth_token_error_helper(data, error)

    def test_oauth_token_code_reuse(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }
        error = {
            "error": "invalid_grant",
            "error_description": "\"code\" in request is already used."
        }
        self._test_oauth_token_error_helper(data, error)

        access_token = db.session.query(OAuth2AccessToken).filter_by(access_token=token["access_token"]).first()
        self.assertTrue(access_token.revoked)
        refresh_token = db.session.query(OAuth2RefreshToken).filter_by(refresh_token=token["refresh_token"]).first()
        self.assertTrue(refresh_token.revoked)

    def test_oauth_authorization_code_expiry(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }
        error = {
            "error": "invalid_grant",
            "error_description": "\"code\" in request is expired."
        }
        with freeze_time() as frozen_datetime:
            frozen_datetime.tick(timedelta(minutes=60))
            self._test_oauth_token_error_helper(data, error)

    def test_oauth_token_code_mismatch(self):
        application1 = self.create_oauth_app()
        application2 = self.create_oauth_app()[1]
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application1, redirect_uri, True)

        data = {
            "client_id": application2["client_id"],
            "client_secret": application2["client_secret"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }
        error = {
            "error": "invalid_grant",
            "error_description": "Invalid \"code\" in request."
        }
        self._test_oauth_token_error_helper(data, error)

    def test_oauth_authorize_decline(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": application["client_id"],
            "response_type": "code",
            "scope": "test-scope-1",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback",
        }

        self.authorize_oauth_prompt_helper(query_string)

        with login_user(self.user2):
            response = self.client.post("/oauth2/authorize/confirm", query_string=query_string, data={
                    "confirm": "no",
                    "csrf_token": g.csrf_token
            })
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, "https://example.com/callback?error=access_denied")

    def test_oauth_authorize_missing_client_id(self):
        application = self.create_oauth_app()
        query_string = {
            "response_type": "code",
            "scope": "test-scope-1",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback",
        }
        error = {"name": "invalid_client", "description": ""}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_authorize_invalid_client_id(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": "asb",
            "response_type": "code",
            "scope": "test-scope-1",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback",
        }
        error = {"name": "invalid_client", "description": ""}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_authorize_missing_response_type(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": application["client_id"],
            "scope": "test-scope-1",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback",
        }
        error = {"name": "unsupported_response_type", "description": "response_type=None is not supported"}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_authorize_invalid_response_type(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": application["client_id"],
            "response_type": "invalid",
            "scope": "test-scope-1",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback",
        }
        error = {"name": "unsupported_response_type", "description": "response_type=invalid is not supported"}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_authorize_missing_scope(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": application["client_id"],
            "response_type": "code",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback",
        }
        error = {"name": "invalid_scope", "description": "The requested scope is invalid, unknown, or malformed."}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_authorize_invalid_scope(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": application["client_id"],
            "response_type": "code",
            "scope": "test-scope-abc",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback",
        }
        error = {"name": "invalid_scope", "description": "The requested scope is invalid, unknown, or malformed."}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_authorize_missing_redirect_uri(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": application["client_id"],
            "response_type": "code",
            "scope": "test-scope-1",
            "state": "random-state",
        }
        error = {"name": "invalid_request", "description": "Missing \"redirect_uri\" in request."}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_authorize_invalid_redirect_uri(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": application["client_id"],
            "response_type": "code",
            "scope": "test-scope-1",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback2",
        }
        error = {"name": "invalid_request", "description": "Redirect URI https://example.com/callback2 is not supported by client."}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_authorize_cancel_url(self):
        application = self.create_oauth_app()
        with login_user(self.user2):
            response = self.client.get(
                "/oauth2/authorize",
                query_string={
                    "client_id": application["client_id"],
                    "response_type": "code",
                    "scope": "test-scope-1",
                    "state": "random-state",
                    "redirect_uri": "https://example.com/callback",
                }
            )
            props = json.loads(self.get_context_variable("props"))
            self.assertTrue(props["cancel_url"], "https://example.com/callback?error=access_denied")

    def test_oauth_authorize_logged_out(self):
        application = self.create_oauth_app()
        response = self.client.get(
            "/oauth2/authorize",
            query_string={
                "client_id": application["client_id"],
                "response_type": "code",
                "scope": "test-scope-1",
                "state": "random-state",
                "redirect_uri": "https://example.com/callback",
            }
        )
        self.assertEqual(response.status_code, 302)
        parsed = urlparse(response.location)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.scheme + "://" + parsed.netloc, self.app.config["MUSICBRAINZ_SERVER"])
        self.assertEqual(parsed.path, "/login")

        fragment_args = parse_qs(parsed.query)
        self.assertEqual(unquote(fragment_args["returnto"][0]), f"http://{self.app.config['SERVER_NAME']}/oauth2/authorize?client_id={application['client_id']}&response_type=code&scope=test-scope-1&state=random-state&redirect_uri=https://example.com/callback")

    @pytest.mark.skip
    def test_oauth_authorize_parameter_reuse(self):
        application = self.create_oauth_app()
        query_string = MultiDict([
            ("client_id", application["client_id"]),
            ("scope", "test-scope-1"),
            ("state", "random-state"),
            ("redirect_uri", "https://example.com/callback"),
            ("response_type", "code"),
            ("response_type", "token"),
        ])
        error = {"name": "invalid_request", "description": ""}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_authorize_multiple_redirect_uris(self):
        application = self.create_oauth_app(redirect_uris=[
            "https://example.com/callback1",
            "https://example.com/callback2"
        ])
        code1 = self.authorize_success_for_token_grant_helper(application, "https://example.com/callback1")
        self.token_success_token_grant_helper(application, code1, "https://example.com/callback1")
        code2 = self.authorize_auto_approval_prompt_helper(application, "https://example.com/callback2")
        self.token_success_token_grant_helper(application, code2, "https://example.com/callback2")

    def authorize_auto_approval_prompt_helper(self, application, redirect_uri, only_one_code=False, approval_prompt=None):
        query_string = {
            "client_id": application["client_id"],
            "response_type": "code",
            "scope": "test-scope-1",
            "state": "random-state",
            "redirect_uri": redirect_uri,
        }
        if approval_prompt is not None:
            query_string["approval_prompt"] = approval_prompt

        with login_user(self.user2):
            response = self.client.get("/oauth2/authorize", query_string=query_string)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.startswith(redirect_uri))
            parsed = urlparse(response.location)
            query_args = parse_qs(parsed.query)

            self.assertIsNone(query_args.get("error"))

            self.assertEqual(len(query_args["state"]), 1)
            self.assertEqual(query_args["state"][0], "random-state")

            self.assertEqual(len(query_args["code"]), 1)
            codes = db.session.query(OAuth2AuthorizationCode).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2AuthorizationCode.client_id == OAuth2Client.id,
                OAuth2AuthorizationCode.user_id == self.user2.id,
            ).all()
            codes = {code.code for code in codes}
            self.assertIn(query_args["code"][0], codes)
            if only_one_code:
                self.assertEqual(len(codes), 1)

            return query_args["code"][0]

    def test_oauth_approval_prompt_auto(self):
        application = self.create_oauth_app(redirect_uris=[
            "https://example.com/callback1",
            "https://example.com/callback2"
        ])
        code1 = self.authorize_success_for_token_grant_helper(application, "https://example.com/callback1")
        self.token_success_token_grant_helper(application, code1, "https://example.com/callback1")
        code2 = self.authorize_auto_approval_prompt_helper(application, "https://example.com/callback2",
                                                           approval_prompt="auto")
        self.token_success_token_grant_helper(application, code2, "https://example.com/callback2")

    def test_oauth_approval_prompt_force(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        self.token_success_token_grant_helper(application, code, redirect_uri, True)

        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, False, approval_prompt="force")
        self.token_success_token_grant_helper(application, code, redirect_uri, False)

    def test_oauth_approval_prompt_none(self):
        application = self.create_oauth_app(redirect_uris=[
            "https://example.com/callback1",
            "https://example.com/callback2"
        ])
        code1 = self.authorize_success_for_token_grant_helper(application, "https://example.com/callback1")
        self.token_success_token_grant_helper(application, code1, "https://example.com/callback1")
        code2 = self.authorize_auto_approval_prompt_helper(application, "https://example.com/callback2")
        self.token_success_token_grant_helper(application, code2, "https://example.com/callback2")

    def test_oauth_approval_prompt_invalid(self):
        application = self.create_oauth_app(redirect_uris=[
            "https://example.com/callback1",
            "https://example.com/callback2"
        ])
        query_string = {
            "client_id": application["client_id"],
            "response_type": "code",
            "scope": "test-scope-1",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback2",
            "approval_prompt": "invalid",
        }
        error = {"name": "invalid_request", "description": "Invalid \"approval_prompt\" in request."}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_approval_prompt_scope_mismatch(self):
        redirect_uri1 = "https://example.com/callback1"
        redirect_uri2 = "https://example.com/callback2"
        application = self.create_oauth_app(redirect_uris=[redirect_uri1, redirect_uri2])
        code1 = self.authorize_success_for_token_grant_helper(application, redirect_uri1)
        self.token_success_token_grant_helper(application, code1, redirect_uri1)

        query_string = {
            "client_id": application["client_id"],
            "response_type": "token",
            "scope": "test-scope-1 test-scope-2",
            "state": "random-state",
            "redirect_uri": redirect_uri2,
        }
        with login_user(self.user2):
            response = self.client.get("/oauth2/authorize", query_string=query_string)
            self.assertTemplateUsed("oauth/prompt.html")
            props = json.loads(self.get_context_variable("props"))

            self.assertEqual(props["client_name"], "test-client")
            self.assertEqual(props["scopes"], [
                {"name": "test-scope-1", "description": "Test Scope 1"},
                {"name": "test-scope-2", "description": "Test Scope 2"}
            ])
            self.assertEqual(props["cancel_url"], redirect_uri2 + "?error=access_denied")
            self.assertEqual(props["csrf_token"], g.csrf_token)

            parsed = urlparse(props["submission_url"])
            self.assertEqual(parsed.path, "/oauth2/authorize/confirm")
            self.assertEqual(parse_qs(parsed.query), {k: [v] for k, v in query_string.items()})

    def test_oauth_basic_auth(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)

        auth = base64.b64encode((application["client_id"] + ":" + application["client_secret"]).encode("utf-8")).decode("utf-8")

        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post(
                "/oauth2/token",
                data={
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
                headers={"Authorization": f"Basic {auth}"}
            )
            self.assert200(response)
            data = response.json
            self.assertEqual(data["expires_in"], 3600)
            self.assertEqual(data["token_type"], "Bearer")

            access_tokens = db.session.query(OAuth2AccessToken).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2AccessToken.client_id == OAuth2Client.id,
                OAuth2AccessToken.user_id == self.user2.id,
            ).all()
            access_tokens = {token.access_token for token in access_tokens}
            self.assertIn(data["access_token"], access_tokens)

            refresh_tokens = db.session.query(OAuth2RefreshToken).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2RefreshToken.client_id == OAuth2Client.id,
                OAuth2RefreshToken.user_id == self.user2.id,
            ).all()
            refresh_tokens = {token.refresh_token for token in refresh_tokens}
            self.assertIn(data["refresh_token"], refresh_tokens)

    def test_oauth_form_post_model(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        query_string = {
            "client_id": application["client_id"],
            "response_type": "code",
            "scope": "test-scope-1",
            "state": "random-state",
            "redirect_uri": redirect_uri,
            "response_mode": "form_post"
        }
        self.authorize_oauth_prompt_helper(query_string)

        with login_user(self.user2):
            response = self.client.post("/oauth2/authorize/confirm", query_string=query_string, data={
                "confirm": "yes",
                "csrf_token": g.csrf_token
            })
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed("oauth/authorize_form_post.html")
            self.assertEqual(self.get_context_variable("redirect_uri"), redirect_uri)

            query_args = self.get_context_variable("values")
            self.assertIsNone(query_args.get("error"))

            self.assertEqual(len(query_args["state"]), 1)
            self.assertEqual(query_args["state"][0], "random-state")

            self.assertEqual(len(query_args["code"]), 1)
            codes = db.session.query(OAuth2AuthorizationCode).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2AuthorizationCode.client_id == OAuth2Client.id,
                OAuth2AuthorizationCode.user_id == self.user2.id,
            ).all()
            codes = {code.code for code in codes}
            self.assertIn(query_args["code"][0], codes)

            code = query_args["code"][0]
            self.token_success_token_grant_helper(application, code, redirect_uri, True)
