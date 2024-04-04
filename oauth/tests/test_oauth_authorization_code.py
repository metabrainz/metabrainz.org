import json
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs, unquote

from flask import g
from flask_testing import TestCase
from sqlalchemy import delete

import oauth
from oauth.authorization_grant import AuthorizationCodeGrant
from oauth.login import User
from oauth.model import db, OAuth2Scope, OAuth2Client, OAuth2Token, OAuth2AuthorizationCode
from oauth.tests import login_user


class OAuthTestCase(TestCase):

    def create_app(self):
        app = oauth.create_app()
        app.config['TESTING'] = False
        app.config['DEBUG'] = False
        return app

    def setUp(self):
        self.user1 = User(user_id=1, user_name="test-user-1")
        self.user2 = User(user_id=2, user_name="test-user-2")

        scope = OAuth2Scope()
        scope.name = "test-scope-1"
        scope.description = "Test Scope 1"
        db.session.add(scope)
        db.session.commit()

    def tearDown(self):
        db.session.execute(delete(OAuth2Token))
        db.session.execute(delete(OAuth2AuthorizationCode))
        db.session.execute(delete(OAuth2Scope))
        db.session.execute(delete(OAuth2Client))
        db.session.commit()

    def create_oauth_app(self, owner=None, redirect_uris=None):
        if owner is None:
            owner = self.user1
        data = {
            "client_name": "test-client",
            "description": "test-description",
            "website": "https://example.com",
        }
        if redirect_uris is None:
            redirect_uris = ["https://example.com/callback"]

        for idx, redirect_uri in enumerate(redirect_uris):
            data[f"redirect_uris.{idx}"] = redirect_uri

        with login_user(owner):
            self.client.get("/oauth2/client/create")
            data["csrf_token"] = g.csrf_token
            self.client.post("/oauth2/client/create", data=data, follow_redirects=True)

            applications = json.loads(self.get_context_variable("props"))["applications"]
            if len(applications) == 1:
                return applications[0]
            else:
                return applications

    def _test_oauth_authorize_success_helper(self, application, redirect_uri, only_one_code=False):
        with login_user(self.user2):
            response = self.client.get(
                "/oauth2/authorize",
                query_string={
                    "client_id": application["client_id"],
                    "response_type": "code",
                    "scope": "test-scope-1",
                    "state": "random-state",
                    "redirect_uri": redirect_uri,
                }
            )
            self.assertTemplateUsed("oauth/prompt.html")
            props = json.loads(self.get_context_variable("props"))
            self.assertEqual(props, {
                "client_name": "test-client",
                "scopes": [{"name": "test-scope-1", "description": "Test Scope 1"}],
                "cancel_url": redirect_uri + "?error=access_denied",
                "csrf_token": g.csrf_token,
            })

            response = self.client.post(
                "/oauth2/authorize",
                query_string={
                    "client_id": application["client_id"],
                    "response_type": "code",
                    "scope": "test-scope-1",
                    "state": "random-state",
                    "redirect_uri": redirect_uri,
                },
                data={
                    "confirm": "yes",
                    "csrf_token": g.csrf_token
                }
            )
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.startswith(redirect_uri))
            parsed = urlparse(response.location)
            query_args = parse_qs(parsed.query)
            print(parsed.query)
            
            self.assertIsNone(query_args.get("error"))
            
            self.assertEqual(len(query_args["state"]), 1)
            self.assertEqual(query_args["state"][0], "random-state")

            self.assertEqual(len(query_args["code"]), 1)
            codes = db.session.query(OAuth2AuthorizationCode).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2AuthorizationCode.user_id == self.user2.id,
            ).all()
            codes = {code.code for code in codes}
            self.assertIn(query_args["code"][0], codes)
            if only_one_code:
                self.assertEqual(len(codes), 1)

            return query_args["code"][0]

    def _test_oauth_token_success_helper(self, application, code, redirect_uri, only_one_token=False):
        with patch.object(
            AuthorizationCodeGrant,
            "authenticate_user",
            return_value=self.user2
        ):
            response = self.client.post(
                "/oauth2/token",
                data={
                    "client_id": application["client_id"],
                    "client_secret": application["client_secret"],
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                    "code": code,
                }
            )
            print(response.json)
            self.assert200(response)
            data = response.json
            self.assertEqual(data["expires_in"], 864000)
            self.assertEqual(data["token_type"], "Bearer")
            tokens = db.session.query(OAuth2Token).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2Token.user_id == self.user2.id,
            ).all()
            tokens = {token.access_token for token in tokens}
            self.assertIn(data["access_token"], tokens)
            if only_one_token:
                self.assertEqual(len(tokens), 1)

    def test_oauth_token(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)
        self._test_oauth_token_success_helper(application, code, redirect_uri, True)

    def _test_oauth_token_error_helper(self, data, error):
        with patch.object(AuthorizationCodeGrant,"authenticate_user", return_value=self.user2):
            response = self.client.post("/oauth2/token", data=data)
            self.assert400(response)
            self.assertEqual(response.json, error)

    def test_oauth_token_invalid_client_id(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)

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
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)

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
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)

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
        print(application1)
        print(application2)
        redirect_uri = "https://example.com/callback"
        code = self._test_oauth_authorize_success_helper(application1, redirect_uri, True)

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
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)

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
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)

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
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "redirect_uri": redirect_uri,
            "code": code,
        }
        error = {"error": "unsupported_grant_type"}
        self._test_oauth_token_error_helper(data, error)

    def test_oauth_token_missing_redirect_uri(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)

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
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)

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
        code = self._test_oauth_authorize_success_helper(application, redirect_uri1, True)

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
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)

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
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)

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
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)
        self._test_oauth_token_success_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }
        error = {
            "error": "invalid_grant",
            "error_description": "Invalid \"code\" in request."
        }
        self._test_oauth_token_error_helper(data, error)

    def test_oauth_token_code_mismatch(self):
        application1 = self.create_oauth_app()
        application2 = self.create_oauth_app()[1]
        redirect_uri = "https://example.com/callback"
        code = self._test_oauth_authorize_success_helper(application1, redirect_uri, True)

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
            self.assertTemplateUsed("oauth/prompt.html")
            props = json.loads(self.get_context_variable("props"))
            self.assertEqual(props, {
                "client_name": "test-client",
                "scopes": [{"name": "test-scope-1", "description": "Test Scope 1"}],
                "cancel_url": "https://example.com/callback?error=access_denied",
                "csrf_token": g.csrf_token,
            })

            response = self.client.post(
                "/oauth2/authorize",
                query_string={
                    "client_id": application["client_id"],
                    "response_type": "code",
                    "scope": "test-scope-1",
                    "state": "random-state",
                    "redirect_uri": "https://example.com/callback",
                },
                data={
                    "confirm": "no",
                    "csrf_token": g.csrf_token
                }
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, "https://example.com/callback?error=access_denied")

    def _test_oauth_authorize_helper(self, user, query_string, error):
        with login_user(user):
            response = self.client.get(
                "/oauth2/authorize",
                query_string=query_string,
            )
            self.assertTemplateUsed("oauth/error.html")
            props = json.loads(self.get_context_variable("props"))
            self.assertEqual(props["error"], error)

            response = self.client.post(
                "/oauth2/authorize",
                query_string=query_string,
                data={
                    "confirm": "yes",
                    "csrf_token": g.csrf_token
                }
            )
            self.assertTemplateUsed("oauth/error.html")
            props = json.loads(self.get_context_variable("props"))
            self.assertEqual(props["error"], error)

    def test_oauth_authorize_missing_client_id(self):
        application = self.create_oauth_app()
        query_string = {
            "response_type": "code",
            "scope": "test-scope-1",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback",
        }
        error = {"name": "invalid_client", "description": ""}
        self._test_oauth_authorize_helper(self.user2, query_string, error)

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
        self._test_oauth_authorize_helper(self.user2, query_string, error)

    def test_oauth_authorize_missing_response_type(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": application["client_id"],
            "scope": "test-scope-1",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback",
        }
        error = {"name": "unsupported_response_type", "description": "response_type=None is not supported"}
        self._test_oauth_authorize_helper(self.user2, query_string, error)

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
        self._test_oauth_authorize_helper(self.user2, query_string, error)

    def test_oauth_authorize_missing_scope(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": application["client_id"],
            "response_type": "code",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback",
        }
        error = {"name": "invalid_scope", "description": "The requested scope is invalid, unknown, or malformed."}
        self._test_oauth_authorize_helper(self.user2, query_string, error)

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
        self._test_oauth_authorize_helper(self.user2, query_string, error)

    def test_oauth_authorize_missing_redirect_uri(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": application["client_id"],
            "response_type": "code",
            "scope": "test-scope-1",
            "state": "random-state",
        }
        error = {"name": "invalid_request", "description": "Missing \"redirect_uri\" in request."}
        self._test_oauth_authorize_helper(self.user2, query_string, error)

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
        self._test_oauth_authorize_helper(self.user2, query_string, error)

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
        self.assertEqual(unquote(fragment_args["next"][0]), f"http://{self.app.config['SERVER_NAME']}/oauth2/authorize?client_id={application['client_id']}&response_type=code&scope=test-scope-1&state=random-state&redirect_uri=https://example.com/callback")

    def test_oauth_authorize_multiple_redirect_uris(self):
        application = self.create_oauth_app(redirect_uris=[
            "https://example.com/callback1",
            "https://example.com/callback2"
        ])
        self._test_oauth_authorize_success_helper(application, "https://example.com/callback1")
        self._test_oauth_authorize_success_helper(application, "https://example.com/callback2")
