import base64
import pytest

from oauth.tests import OAuthTestCase


class RevocationTestCase(OAuthTestCase):

    def _test_oauth_introspection_error_helper(self, data):
        response = self.client.post("/oauth2/introspect", data=data)
        self.assert200(response)
        self.assertEqual(response.json["active"], False)

    def test_oauth_revoke_success(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        self.temporary_login(self.user2)
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["access_token"],
        }
        self.introspection_success_helper(data)

        response = self.client.post("/oauth2/revoke", data=data)
        self.assert200(response)
        self.assertEqual(response.json, {})

        self._test_oauth_introspection_error_helper(data)

    def test_oauth_revoke_access_token_refresh_still_works(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        self.temporary_login(self.user2)
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["access_token"],
        }
        self.introspection_success_helper(data)

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

        self.temporary_login(self.user2)
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["refresh_token"],
        }
        self.introspection_success_helper(data)

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

        self.temporary_login(self.user2)
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "token": token["refresh_token"],
        }
        response = self.client.post("/oauth2/revoke", data=data)
        self.assert401(response)
        self.assertEqual(response.json, {"error": "invalid_client"})

    @pytest.mark.skip
    def test_oauth_revoke_different_credentials(self):
        application = self.create_oauth_app()
        application2 = self.create_oauth_app()[1]
        redirect_uri = "https://example.com/callback"

        self.temporary_login(self.user2)
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application2["client_id"],
            "client_secret": application2["client_secret"],
            "token": token["refresh_token"],
        }
        response = self.client.post("/oauth2/revoke", data=data)
        self.assert401(response)
        self.assertEqual(response.json, {"error": "invalid_client"})

    def test_oauth_revoke_missing_client_id(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        self.temporary_login(self.user2)
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_secret": application["client_secret"],
            "token": token["refresh_token"],
        }
        response = self.client.post("/oauth2/revoke", data=data)
        self.assert401(response)
        self.assertEqual(response.json, {"error": "invalid_client"})

    def test_oauth_revoke_invalid_client_id(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        self.temporary_login(self.user2)
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_secret"],
            "client_secret": application["client_id"],
            "token": token["refresh_token"],
        }
        response = self.client.post("/oauth2/revoke", data=data)
        self.assert400(response)
        self.assertEqual(response.json, {"error": "invalid_client"})

    def test_oauth_revoke_missing_client_secret(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        self.temporary_login(self.user2)
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "token": token["refresh_token"],
        }
        response = self.client.post("/oauth2/revoke", data=data)
        self.assert401(response)
        self.assertEqual(response.json, {"error": "invalid_client"})

    def test_oauth_revoke_invalid_client_secret(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        self.temporary_login(self.user2)
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_id"],
            "token": token["refresh_token"],
        }

        response = self.client.post("/oauth2/revoke", data=data)
        self.assert401(response)
        self.assertEqual(response.json, {"error": "invalid_client"})

    def test_oauth_revoke_invalid_token_type_hint(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        self.temporary_login(self.user2)
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)
        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["refresh_token"],
            "token_type_hint": "code"
        }
        
        response = self.client.post("/oauth2/revoke", data=data)
        self.assert401(response)
        self.assertEqual(response.json, {"error": "unsupported_token_type"})

    def test_oauth_revoke_wrong_token_type_hint(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        self.temporary_login(self.user2)
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)
        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token["refresh_token"],
            "token_type_hint": "access_token"
        }

        response = self.client.post("/oauth2/revoke", data=data)
        self.assert200(response)
        self.assertEqual(response.json, {})
    
    def test_oauth_revoke_wrong_token(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        self.temporary_login(self.user2)
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)
        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": "refresh_token",
        }

        response = self.client.post("/oauth2/revoke", data=data)
        self.assert200(response)
        self.assertEqual(response.json, {})

    def test_oauth_revoke_basic_auth(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        self.temporary_login(self.user2)
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        auth = base64.b64encode((application["client_id"] + ":" + application["client_secret"]).encode("utf-8")).decode("utf-8")

        response = self.client.post(
            "/oauth2/revoke",
            data={"token": token["access_token"]},
            headers={"Authorization": "Basic " + auth}
        )
        self.assert200(response)
        self.assertEqual(response.json, {})

    def test_oauth_revoke_client_credentials(self):
        application = self.create_oauth_app()
        self.app.config["OAUTH2_WHITELISTED_CCG_CLIENTS"] = [
            application["client_id"],
        ]

        self.temporary_login(self.user2)
        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "client_credentials",
            "scope": "profile",
        }
        response = self.client.post("/oauth2/token", data=data)
        self.assertEqual(response.status_code, 200)
        token = response.json["access_token"]

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "token": token,
        }
        response = self.client.post("/oauth2/revoke", data=data)
        self.assert200(response)
        self.assertEqual(response.json, {})

        response = self.client.post("/oauth2/introspect", data=data)
        self.assert200(response)
        self.assertEqual(response.json["active"], False)
