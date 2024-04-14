from unittest.mock import patch
from urllib.parse import urlparse, parse_qs

from flask import g

from oauth.model import db, OAuth2Client, OAuth2AccessToken, OAuth2RefreshToken
from oauth.refresh_grant import RefreshTokenGrant
from oauth.tests import login_user, OAuthTestCase


class RefreshGrantTestCase(OAuthTestCase):

    def test_oauth_token_refresh_success(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        self.refresh_grant_success_helper(application, token)

    def _test_oauth_token_error_helper(self, access_token, data, error):
        with patch.object(RefreshTokenGrant, "authenticate_user", return_value=self.user2):
            response = self.client.post("/oauth2/token", data=data)
            self.assert400(response)
            self.assertEqual(response.json, error)

            old_token = db.session.query(OAuth2AccessToken).filter_by(access_token=access_token).first()
            self.assertFalse(old_token.revoked)

    def test_oauth_token_refresh_missing_client_id(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)
        data = {
            "client_secret": application["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        }
        error = {"error": "invalid_client"}
        self._test_oauth_token_error_helper(token["access_token"], data, error)

    def test_oauth_token_refresh_invalid_client_id(self):
        application = self.create_oauth_app()
        application2 = self.create_oauth_app()[1]
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)
        data = {
            "client_id": application2["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        }
        error = {"error": "invalid_client"}
        self._test_oauth_token_error_helper(token["access_token"], data, error)

    def test_oauth_token_refresh_missing_client_secret(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)
        data = {
            "client_id": application["client_id"],
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        }
        error = {"error": "invalid_client"}
        self._test_oauth_token_error_helper(token["access_token"], data, error)

    def test_oauth_token_refresh_invalid_client_secret(self):
        application = self.create_oauth_app()
        application2 = self.create_oauth_app()[1]
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)
        data = {
            "client_id": application["client_id"],
            "client_secret": application2["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        }
        error = {"error": "invalid_client"}
        self._test_oauth_token_error_helper(token["access_token"], data, error)

    def test_oauth_token_refresh_different_client(self):
        application = self.create_oauth_app()
        application2 = self.create_oauth_app()[1]
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)
        data = {
            "client_id": application2["client_id"],
            "client_secret": application2["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        }
        error = {"error": "invalid_grant"}
        self._test_oauth_token_error_helper(token["access_token"], data, error)

    def test_oauth_token_refresh_missing_refresh_token(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)
        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "refresh_token",
        }
        error = {"error": "invalid_request", "error_description": "Missing \"refresh_token\" in request."}
        self._test_oauth_token_error_helper(token["access_token"], data, error)

    def test_oauth_token_refresh_invalid_refresh_token(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)
        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": token["access_token"],
        }
        error = {"error": "invalid_grant"}
        self._test_oauth_token_error_helper(token["access_token"], data, error)

    def test_oauth_token_refresh_retains_original_scope(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        query_string = {
            "client_id": application["client_id"],
            "response_type": "code",
            "scope": "test-scope-1 test-scope-2",
            "state": "random-state",
            "redirect_uri": redirect_uri,
        }

        with login_user(self.user2):
            self.client.get("/oauth2/authorize", query_string=query_string)
            response = self.client.post("/oauth2/authorize", query_string=query_string, data={
                "confirm": "yes",
                "csrf_token": g.csrf_token
            })
            print(response.location)
            print(response.json)
            parsed = urlparse(response.location)
            query_args = parse_qs(parsed.query)
            code = query_args["code"][0]

        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)
        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "refresh_token",
            "scope": "test-scope-1",
            "refresh_token": token["refresh_token"],
        }
        with patch.object(
            RefreshTokenGrant,
            "authenticate_user",
            return_value=self.user2
        ):
            response = self.client.post("/oauth2/token", data=data)
            self.assert200(response)

            new_token = response.json

            access_token = db.session.query(OAuth2AccessToken).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2Client.id == OAuth2AccessToken.client_id,
                OAuth2AccessToken.user_id == self.user2.id,
                OAuth2AccessToken.revoked == False,
            ).first()
            self.assertEqual(new_token["access_token"], access_token.access_token)
            self.assertSetEqual({"test-scope-1"}, {s.name for s in access_token.scopes})

            refresh_token = db.session.query(OAuth2RefreshToken).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2Client.id == OAuth2RefreshToken.client_id,
                OAuth2RefreshToken.user_id == self.user2.id,
                OAuth2RefreshToken.revoked == False,
            ).first()
            self.assertEqual(new_token["refresh_token"], refresh_token.refresh_token)
            self.assertSetEqual({"test-scope-1", "test-scope-2"}, {s.name for s in refresh_token.scopes})
