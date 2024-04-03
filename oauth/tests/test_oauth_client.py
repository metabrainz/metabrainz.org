import json
from unittest.mock import patch

import flask_testing
from flask import g
from sqlalchemy import delete

import oauth
from oauth.login import User
from oauth.model import OAuth2Client, db


class OAuthTestCase(flask_testing.TestCase):

    def create_app(self):
        app = oauth.create_app()
        app.config["DEBUG"] = False
        return app

    def setUp(self):
        self.user = User(1, "test-user")
        patcher = patch("oauth.login.load_user_from_request", return_value=self.user)
        self.mock_load_user_from_request = patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        db.session.execute(delete(OAuth2Client))
        db.session.commit()

    def test_oauth_client_create(self):
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

        response = self.client.post(f"/oauth2/client/delete/{application['client_id']}", follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        props = json.loads(self.get_context_variable("props"))
        self.assertListEqual(props["applications"], [])
