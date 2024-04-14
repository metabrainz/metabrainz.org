import json
from datetime import datetime
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs, unquote

from flask import g
from flask_testing import TestCase
from sqlalchemy import delete

import oauth
from oauth.authorization_grant import AuthorizationCodeGrant
from oauth.login import User
from oauth.model import db, OAuth2Scope, OAuth2Client, OAuth2AccessToken, OAuth2AuthorizationCode, OAuth2RefreshToken
from oauth.refresh_grant import RefreshTokenGrant
from oauth.tests import login_user


class OAuthTestCase(TestCase):

    def create_app(self):
        app = oauth.create_app()
        app.config["TESTING"] = False
        app.config["DEBUG"] = False
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
        db.session.rollback()
        db.session.execute(delete(OAuth2AccessToken))
        db.session.execute(delete(OAuth2RefreshToken))
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
            self.assert200(response)
            data = response.json
            self.assertEqual(data["expires_in"], 864000)
            self.assertEqual(data["token_type"], "Bearer")

            access_tokens = db.session.query(OAuth2AccessToken).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2AccessToken.user_id == self.user2.id,
            ).all()
            access_tokens = {token.access_token for token in access_tokens}
            self.assertIn(data["access_token"], access_tokens)

            refresh_tokens = db.session.query(OAuth2RefreshToken).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2AccessToken.user_id == self.user2.id,
            ).all()
            refresh_tokens = {token.refresh_token for token in refresh_tokens}
            self.assertIn(data["refresh_token"], refresh_tokens)

            if only_one_token:
                self.assertEqual(len(access_tokens), 1)
                self.assertEqual(len(refresh_tokens), 1)

            return data

    def _test_oauth_introspection_success_helper(self, data, expires_in=864000):
        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/introspect", data=data)
            self.assert200(response)
            self.assertEqual(response.json["active"], True)
            self.assertEqual(response.json["client_id"], data["client_id"])
            self.assertEqual(response.json["issued_by"], "https://metabrainz.org/")
            self.assertEqual(response.json["scope"], ["test-scope-1"])
            self.assertEqual(response.json["sub"],  self.user2.user_name)
            self.assertEqual(response.json["token_type"],  "Bearer")
            self.assertEqual(response.json["metabrainz_user_id"], self.user2.id)
            self.assertIsNotNone(response.json["issued_at"])
            self.assertEqual(response.json["expires_at"] - response.json["issued_at"], expires_in)

    def _test_oauth_introspection_error_helper(self, data):
        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/introspect", data=data)
            self.assert200(response)
            self.assertEqual(response.json["active"], False)

    def test_oauth_revoke_success(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)
        token = self._test_oauth_token_success_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["access_token"],
        }
        self._test_oauth_introspection_success_helper(data)

        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/revoke", data=data)
            self.assert200(response)
            self.assertEqual(response.json, {})

        self._test_oauth_introspection_error_helper(data)

    def _test_oauth_refresh_token(self, application, token):
        with patch.object(
            RefreshTokenGrant,
            "authenticate_user",
            return_value=self.user2
        ):
            response = self.client.post(
                "/oauth2/token",
                data={
                    "client_id": application["client_id"],
                    "client_secret": application["client_secret"],
                    "grant_type": "refresh_token",
                    "refresh_token": token["refresh_token"],
                }
            )
            self.assert200(response)

            old_token = db.session.query(OAuth2AccessToken).filter_by(access_token=token["access_token"]).first()
            self.assertTrue(old_token.revoked)

            new_token = response.json
            self.assertEqual(new_token["expires_in"], 3600)
            self.assertEqual(new_token["token_type"], "Bearer")

            access_tokens = db.session.query(OAuth2AccessToken).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2AccessToken.user_id == self.user2.id,
                OAuth2AccessToken.revoked == False,
            ).all()
            access_tokens = {token.access_token for token in access_tokens}
            self.assertIn(new_token["access_token"], access_tokens)

            refresh_tokens = db.session.query(OAuth2RefreshToken).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2AccessToken.user_id == self.user2.id,
                OAuth2AccessToken.revoked == False,
            ).all()
            refresh_tokens = {token.refresh_token for token in refresh_tokens}
            self.assertIn(new_token["refresh_token"], refresh_tokens)

    def test_oauth_revoke_access_token_refresh_still_works(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)
        token = self._test_oauth_token_success_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["access_token"],
        }
        self._test_oauth_introspection_success_helper(data)

        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/revoke", data=data)
            self.assert200(response)
            self.assertEqual(response.json, {})

        self._test_oauth_introspection_error_helper(data)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["refresh_token"],
        }
        self._test_oauth_introspection_success_helper(data)
        self._test_oauth_refresh_token(application, token)

    def test_oauth_revoke_refresh_token(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)
        token = self._test_oauth_token_success_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["refresh_token"],
        }
        self._test_oauth_introspection_success_helper(data)

        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/revoke", data=data)
            self.assert200(response)
            self.assertEqual(response.json, {})

        self._test_oauth_introspection_error_helper(data)

        # revoking refresh token revokes access token as well
        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["access_token"],
        }
        self._test_oauth_introspection_error_helper(data)

    def test_oauth_revoke_missing_credentials(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)
        token = self._test_oauth_token_success_helper(application, code, redirect_uri, True)

        data = {
            "token": token["refresh_token"],
        }

        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/revoke", data=data)
            self.assert400(response)
            self.assertEqual(response.json, {"error": "invalid_client"})

    def test_oauth_revoke_different_credentials(self):
        application = self.create_oauth_app()
        application2 = self.create_oauth_app()[1]
        redirect_uri = "https://example.com/callback"
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)
        token = self._test_oauth_token_success_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application2["client_id"],
            "client_secret": application2["client_id"],
            "token": token["refresh_token"],
        }

        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/revoke", data=data)
            self.assert400(response)
            self.assertEqual(response.json, {"error": "invalid_client"})

    def test_oauth_revoke_missing_client_id(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)
        token = self._test_oauth_token_success_helper(application, code, redirect_uri, True)

        data = {
            "client_secret": application["client_secret"],
            "token": token["refresh_token"],
        }

        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/revoke", data=data)
            self.assert400(response)
            self.assertEqual(response.json, {"error": "invalid_client"})

    def test_oauth_revoke_invalid_client_id(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)
        token = self._test_oauth_token_success_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_secret"],
            "client_secret": application["client_id"],
            "token": token["refresh_token"],
        }

        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/revoke", data=data)
            print(response.json)
            self.assert400(response)
            self.assertEqual(response.json, {"error": "invalid_client"})

    def test_oauth_revoke_missing_client_secret(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)
        token = self._test_oauth_token_success_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "token": token["refresh_token"],
        }

        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/revoke", data=data)
            self.assert400(response)
            self.assertEqual(response.json, {"error": "invalid_client"})

    def test_oauth_revoke_invalid_client_secret(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)
        token = self._test_oauth_token_success_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_id"],
            "token": token["refresh_token"],
        }

        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/revoke", data=data)
            self.assert400(response)
            self.assertEqual(response.json, {"error": "invalid_client"})

    def test_oauth_revoke_invalid_token_type_hint(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)
        token = self._test_oauth_token_success_helper(application, code, redirect_uri, True)
        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["refresh_token"],
            "token_type_hint": "code"
        }
        
        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/revoke", data=data)
            self.assert401(response)
            self.assertEqual(response.json, {"error": "unsupported_token_type"})

    def test_oauth_revoke_wrong_token_type_hint(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)
        token = self._test_oauth_token_success_helper(application, code, redirect_uri, True)
        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["refresh_token"],
            "token_type_hint": "access_token"
        }

        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/revoke", data=data)
            self.assert200(response)
            self.assertEqual(response.json, {})
    
    def test_oauth_revoke_wrong_token(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self._test_oauth_authorize_success_helper(application, redirect_uri, True)
        token = self._test_oauth_token_success_helper(application, code, redirect_uri, True)
        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": "refresh_token",
        }

        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/revoke", data=data)
            self.assert200(response)
            self.assertEqual(response.json, {})
