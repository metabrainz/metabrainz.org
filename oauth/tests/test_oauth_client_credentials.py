from oauth.tests import OAuthTestCase


class ClientCredentialsGrantTestCase(OAuthTestCase):

    def test_oauth_client_credentials(self):
        application = self.create_oauth_app()
        self.app.config["OAUTH2_WHITELISTED_CCG_CLIENTS"] = [
            application["client_id"],
        ]
        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "client_credentials",
            "scope": "test-scope-1",
        }
        response = self.client.post("/oauth2/token", data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["token_type"], "Bearer")
        self.assertEqual(response.json["expires_in"], 3600)
        self.assertIn("access_token", response.json)
        self.assertNotIn("refresh_token", response.json)

    def test_oauth_client_credentials_unauthorized_client(self):
        application = self.create_oauth_app()
        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "client_credentials",
            "scope": "test-scope-1",
        }
        response = self.client.post("/oauth2/token", data=data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "unauthorized_client")
