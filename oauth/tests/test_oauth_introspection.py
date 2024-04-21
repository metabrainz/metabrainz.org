from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time

from oauth.refresh_grant import RefreshTokenGrant
from oauth.tests import OAuthTestCase


class IntrospectionTestCase(OAuthTestCase):

    def test_oauth_introspection_success(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["access_token"],
        }
        self.introspection_success_helper(data)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["refresh_token"],
        }
        self.introspection_success_helper(data)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["access_token"],
            "token_type_hint": "access_token",
        }
        self.introspection_success_helper(data)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["refresh_token"],
            "token_type_hint": "refresh_token",
        }
        self.introspection_success_helper(data)

    def _test_oauth_introspection_error_helper(self, data):
        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/introspect", data=data)
            self.assert200(response)
            self.assertEqual(response.json["active"], False)

    def test_oauth_introspection_wrong_token_type_hint(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["access_token"],
            "token_type_hint": "refresh_token",
        }
        self._test_oauth_introspection_error_helper(data)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["refresh_token"],
            "token_type_hint": "access_token",
        }
        self._test_oauth_introspection_error_helper(data)

    def test_oauth_introspection_invalid_token_type_hint(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["access_token"],
            "token_type_hint": "code",
        }
        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/introspect", data=data)
            self.assert401(response)
            self.assertEqual(response.json, {"error": "unsupported_token_type"})

    def test_oauth_introspection_missing_token(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token_type_hint": "access_token",
        }
        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/introspect", data=data)
            self.assert400(response)
            self.assertEqual(response.json, {"error": "invalid_request"})

    def test_oauth_introspection_missing_client_id(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_secret": application["client_secret"],
            "token": token["access_token"],
            "token_type_hint": "access_token",
        }
        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/introspect", data=data)
            self.assert401(response)
            self.assertEqual(response.json, {"error": "invalid_client"})

    def test_oauth_introspection_invalid_client_id(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": "abc",
            "client_secret": application["client_secret"],
            "token": token["access_token"],
            "token_type_hint": "access_token",
        }
        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/introspect", data=data)
            self.assert400(response)
            self.assertEqual(response.json, {"error": "invalid_client"})

    def test_oauth_introspection_missing_client_secret(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "token": token["access_token"],
            "token_type_hint": "access_token",
        }
        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/introspect", data=data)
            self.assert401(response)
            self.assertEqual(response.json, {"error": "invalid_client"})

    def test_oauth_introspection_invalid_client_secret(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": "abc",
            "token": token["access_token"],
            "token_type_hint": "access_token",
        }
        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/introspect", data=data)
            self.assert401(response)
            self.assertEqual(response.json, {"error": "invalid_client"})

    def test_oauth_introspection_invalid_token(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": "abc",
        }
        self._test_oauth_introspection_error_helper(data)

    def test_oauth_introspection_different_client(self):
        application = self.create_oauth_app()
        application2 = self.create_oauth_app()[1]
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application2["client_id"],
            "client_secret": application2["client_secret"],
            "token": token["access_token"],
            "token_type_hint": "access_token",
        }
        self._test_oauth_introspection_error_helper(data)

    def test_oauth_introspection_check_refreshed_token_works(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        old_token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": old_token["access_token"],
        }
        self.introspection_success_helper(data)

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
                    "refresh_token": old_token["refresh_token"],
                }
            )
            self.assert200(response)

        self._test_oauth_introspection_error_helper(data)

        new_token = response.json
        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": new_token["access_token"],
        }
        self.introspection_success_helper(data)

    def test_oauth_introspection_token_expired(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["access_token"],
        }
        self.introspection_success_helper(data)

        with freeze_time() as frozen_time:
            frozen_time.tick(delta=timedelta(hours=25))
            self._test_oauth_introspection_error_helper(data)
