from unittest.mock import patch

from oauth.tests import OAuthTestCase


class RevocationTestCase(OAuthTestCase):

    def _test_oauth_introspection_error_helper(self, data):
        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/introspect", data=data)
            self.assert200(response)
            self.assertEqual(response.json["active"], False)

    def test_oauth_revoke_success(self):
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

        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/revoke", data=data)
            self.assert200(response)
            self.assertEqual(response.json, {})

        self._test_oauth_introspection_error_helper(data)

    def test_oauth_revoke_access_token_refresh_still_works(self):
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
        self.introspection_success_helper(data)
        self.refresh_grant_success_helper(application, token)

    def test_oauth_revoke_refresh_token(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["refresh_token"],
        }
        self.introspection_success_helper(data)

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
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

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
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

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
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

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
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

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
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

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
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

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
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)
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
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)
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
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)
        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": "refresh_token",
        }

        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post("/oauth2/revoke", data=data)
            self.assert200(response)
            self.assertEqual(response.json, {})
