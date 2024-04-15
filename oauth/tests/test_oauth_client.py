import json
from unittest.mock import patch

from flask import g

from oauth.login import User
from oauth.model import OAuth2Client, db, OAuth2AccessToken, OAuth2RefreshToken
from oauth.tests import OAuthTestCase, login_user


class ClientTestCase(OAuthTestCase):

    def setUp(self):
        super().setUp()

        patcher = patch("oauth.login.load_user_from_request", return_value=self.user1)
        self.mock_load_user_from_request = patcher.start()
        self.addCleanup(patcher.stop)

    def create_application(self):
        response = self.client.get("/oauth2/client/create")

        response = self.client.post("/oauth2/client/create", data={
            "client_name": "test-client",
            "description": "test-description",
            "website": "https://example.com",
            "redirect_uris.0": "https://example.com/callback",
            "csrf_token": g.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        props = json.loads(self.get_context_variable("props"))
        application = props["applications"][0]
        self.assertEqual(application["name"], "test-client")

        return application

    def test_oauth_client_create(self):
        application = self.create_application()

        self.assertEqual(application["name"], "test-client")
        self.assertEqual(application["description"], "test-description")
        self.assertEqual(application["website"], "https://example.com")
        self.assertEqual(application["redirect_uris"], ["https://example.com/callback"])

    def test_oauth_client_create_multiple_redirect_uris(self):
        response = self.client.get("/oauth2/client/create")

        response = self.client.post("/oauth2/client/create", data={
            "client_name": "test-client",
            "description": "test-description",
            "website": "https://example.com",
            "redirect_uris.0": "https://example.com/callback",
            "redirect_uris.1": "https://example.com/callback2",
            "csrf_token": g.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        props = json.loads(self.get_context_variable("props"))
        application = props["applications"][0]
        self.assertEqual(application["name"], "test-client")
        self.assertEqual(application["description"], "test-description")
        self.assertEqual(application["website"], "https://example.com")
        self.assertEqual(application["redirect_uris"], [
            "https://example.com/callback",
            "https://example.com/callback2"
        ])

    def test_oauth_client_create_invalid_csrf(self):
        response = self.client.get("/oauth2/client/create")

        response = self.client.post("/oauth2/client/create", data={
            "client_name": "test-client",
            "description": "test-description",
            "website": "https://example.com",
            "redirect_uris.0": "https://example.com/callback"
        })
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["initial_errors"]["csrf_token"], "The CSRF token is missing.")

    def test_oauth_client_create_invalid(self):
        response = self.client.get("/oauth2/client/create")

        response = self.client.post("/oauth2/client/create", data={
            "client_name": "test-client",
            "description": "test-description",
            "redirect_uris.0": "https://example.com/callback",
            "csrf_token": g.csrf_token
        })
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["initial_errors"]["website"], "Homepage field is empty.")

        response = self.client.post("/oauth2/client/create", data={
            "client_name": "test-client",
            "description": "test-description",
            "redirect_uris.0": "javascript:alert('example');",
            "website": "https://example.com",
            "csrf_token": g.csrf_token
        })
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["initial_errors"]["redirect_uris"], [
            "Authorization callback URL is invalid. Authorization callback URL must use http or https."
        ])

        response = self.client.post("/oauth2/client/create", data={
            "client_name": "test-client",
            "description": "test-description",
            "website": "https://example.com",
            "csrf_token": g.csrf_token
        })
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["initial_errors"]["redirect_uris"], [
            "Authorization callback URL field is empty."
        ])

        response = self.client.post("/oauth2/client/create", data={
            "client_name": "te",
            "description": "test-description",
            "website": "https://example.com",
            "redirect_uris.0": "https://example.com/callback",
            "csrf_token": g.csrf_token
        }, follow_redirects=True)
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["initial_errors"]["client_name"], "Application name needs to be at least 3 characters long.")

    def test_oauth_client_edit(self):
        application = self.create_application()

        response = self.client.post(f"/oauth2/client/edit/{application['client_id']}", data={
            "client_name": "test-client-new",
            "description": "test-description",
            "website": "https://example.com",
            "redirect_uris.0": "https://example.com/callback",
            "csrf_token": g.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        props = json.loads(self.get_context_variable("props"))
        application = props["applications"][0]
        self.assertEqual(application["name"], "test-client-new")
        self.assertEqual(application["redirect_uris"], ["https://example.com/callback"])

        response = self.client.post(f"/oauth2/client/edit/{application['client_id']}", data={
            "client_name": "test-client",
            "description": "test-description",
            "website": "https://example.com",
            "redirect_uris.0": "javascript:alert('example');",
            "csrf_token": g.csrf_token
        })
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["initial_errors"]["redirect_uris"], [
            "Authorization callback URL is invalid. Authorization callback URL must use http or https."
        ])

        response = self.client.post(f"/oauth2/client/edit/{application['client_id']}", data={
            "client_name": "test-client-new",
            "description": "test-description",
            "website": "https://example.com",
            "redirect_uris.0": "https://example.com/callback",
            "redirect_uris.1": "https://example.com/callback2",
            "csrf_token": g.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        props = json.loads(self.get_context_variable("props"))
        application = props["applications"][0]
        self.assertEqual(application["name"], "test-client-new")
        self.assertEqual(application["redirect_uris"], [
            "https://example.com/callback",
            "https://example.com/callback2"
        ])

    def test_oauth_client_delete(self):
        application = self.create_application()

        response = self.client.post(f"/oauth2/client/delete/{application['client_id']}", follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        props = json.loads(self.get_context_variable("props"))
        self.assertListEqual(props["applications"], [])

    def test_oauth_client_owner_check(self):
        application = self.create_application()
        user2 = User(2, "test-user-2")

        with patch.object(g, "_login_user", return_value=user2):
            response = self.client.post(f"/oauth2/client/delete/{application['client_id']}", follow_redirects=True)
            self.assertEqual(response.status_code, 403)

            response = self.client.post(f"/oauth2/client/edit/{application['client_id']}", data={
                "client_name": "test-client-new",
                "description": "test-description",
                "website": "https://example.com",
                "redirect_uris.0": "https://example.com/callback",
                "csrf_token": g.csrf_token
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 403)

    def revoke_from_user_helper(self, application):
        with login_user(self.user2):
            response = self.client.post(f"/oauth2/client/{application['client_id']}/revoke/user")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, "/oauth2/client/list")

            tokens = db.session.query(OAuth2AccessToken).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2AccessToken.client_id == OAuth2Client.id,
                OAuth2AccessToken.user_id == self.user2.id,
            )
            for token in tokens:
                self.assertEqual(token.revoked, True)

            tokens = db.session.query(OAuth2RefreshToken).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2RefreshToken.client_id == OAuth2Client.id,
                OAuth2RefreshToken.user_id == self.user2.id,
            )
            for token in tokens:
                self.assertEqual(token.revoked, True)

    def test_oauth_client_revoke_from_user_authorization_grant(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)

        self.revoke_from_user_helper(application)

    def test_oauth_client_revoke_from_user_implicit_grant(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        token = self.authorize_success_helper(application, redirect_uri, True)

        self.revoke_from_user_helper(application)
