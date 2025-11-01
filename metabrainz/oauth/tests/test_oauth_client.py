import json

from flask import g

from metabrainz.model import OAuth2Client, db, OAuth2AccessToken, OAuth2RefreshToken
from metabrainz.oauth.tests import OAuthTestCase


class ClientTestCase(OAuthTestCase):

    def create_application(self):
        response = self.client.get("/profile/applications/create")

        response = self.client.post("/profile/applications/create", data={
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
        self.temporary_login(self.user1)
        application = self.create_application()

        self.assertEqual(application["name"], "test-client")
        self.assertEqual(application["description"], "test-description")
        self.assertEqual(application["website"], "https://example.com")
        self.assertEqual(application["redirect_uris"], ["https://example.com/callback"])

    def test_oauth_client_create_multiple_redirect_uris(self):
        self.temporary_login(self.user1)
        response = self.client.get("/profile/applications/create")

        response = self.client.post("/profile/applications/create", data={
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
        self.temporary_login(self.user1)
        response = self.client.get("/profile/applications/create")

        response = self.client.post("/profile/applications/create", data={
            "client_name": "test-client",
            "description": "test-description",
            "website": "https://example.com",
            "redirect_uris.0": "https://example.com/callback"
        })
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["initial_errors"]["csrf_token"], "The CSRF token is missing.")

    def test_oauth_client_create_invalid(self):
        self.temporary_login(self.user1)
        response = self.client.get("/profile/applications/create")

        response = self.client.post("/profile/applications/create", data={
            "client_name": "test-client",
            "description": "test-description",
            "redirect_uris.0": "https://example.com/callback",
            "csrf_token": g.csrf_token
        })
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["initial_errors"]["website"], "Homepage field is empty.")

        response = self.client.post("/profile/applications/create", data={
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

        response = self.client.post("/profile/applications/create", data={
            "client_name": "test-client",
            "description": "test-description",
            "website": "https://example.com",
            "csrf_token": g.csrf_token
        })
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["initial_errors"]["redirect_uris"], [
            "Authorization callback URL field is empty."
        ])

        response = self.client.post("/profile/applications/create", data={
            "client_name": "te",
            "description": "test-description",
            "website": "https://example.com",
            "redirect_uris.0": "https://example.com/callback",
            "csrf_token": g.csrf_token
        }, follow_redirects=True)
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["initial_errors"]["client_name"], "Application name needs to be at least 3 characters long.")

    def test_oauth_client_edit(self):
        self.temporary_login(self.user1)
        application = self.create_application()

        response = self.client.post(f"/profile/applications/edit/{application['client_id']}", data={
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

        response = self.client.post(f"/profile/applications/edit/{application['client_id']}", data={
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

        response = self.client.post(f"/profile/applications/edit/{application['client_id']}", data={
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
        self.temporary_login(self.user1)
        application = self.create_application()

        response = self.client.get(f"/profile/applications/delete/{application['client_id']}", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed("oauth/delete.html")
        self.maxDiff = None
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["csrf_token"], g.csrf_token)
        self.assertEqual(props["application"], {
            "name": application["name"],
            "description": application["description"],
            "website": application["website"]
        })
        self.assertEqual(props["cancel_url"], "/profile/applications")

        response = self.client.post(f"/profile/applications/delete/{application['client_id']}", data={
            "confirm": "yes",
            "csrf_token": g.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertMessageFlashed("You have deleted an application.", "success")
        self.assertTemplateUsed("oauth/index.html")

        props = json.loads(self.get_context_variable("props"))
        self.assertListEqual(props["applications"], [])

    def test_oauth_client_delete_invalid_csrf(self):
        self.temporary_login(self.user1)
        application = self.create_application()
        response = self.client.post(f"/profile/applications/delete/{application['client_id']}", data={
            "confirm": "yes",
            "csrf_token": "abc"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertMessageFlashed("Failed to delete an application.", "error")
        self.assertTemplateUsed("oauth/index.html")

        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(len(props["applications"]), 1)

    def test_oauth_client_owner_check(self):
        self.temporary_login(self.user1)
        application = self.create_application()

        self.temporary_login(self.user2)
        response = self.client.post(f"/profile/applications/delete/{application['client_id']}", follow_redirects=True)
        self.assertEqual(response.status_code, 403)

        response = self.client.post(f"/profile/applications/edit/{application['client_id']}", data={
            "client_name": "test-client-new",
            "description": "test-description",
            "website": "https://example.com",
            "redirect_uris.0": "https://example.com/callback",
            "csrf_token": g.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 403)

    def revoke_from_user_helper(self, application):
        response = self.client.post(f"/profile/applications/revoke/{application['client_id']}/user")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/profile/applications")

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
        self.temporary_login(self.user1)
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        self.temporary_login(self.user2)
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        self.token_success_token_grant_helper(application, code, redirect_uri, True)
        self.revoke_from_user_helper(application)

    def test_oauth_client_revoke_from_user_implicit_grant(self):
        self.temporary_login(self.user1)
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        self.temporary_login(self.user2)
        self.authorize_success_helper(application, redirect_uri, True)
        self.revoke_from_user_helper(application)

    def test_oauth_client_not_found(self):
        self.temporary_login(self.user1)

        response = self.client.post(f"/profile/applications/revoke/abc/user")
        self.assert404(response)

        response = self.client.post(f"/profile/applications/edit/abc")
        self.assert404(response)

        response = self.client.post(f"/profile/applications/delete/abc")
        self.assert404(response)
