import json
from urllib.parse import urlparse, parse_qs, unquote

import pytest
from flask import g
from werkzeug.datastructures import MultiDict

from oauth.model import db, OAuth2Client, OAuth2AccessToken
from oauth.tests import login_user, OAuthTestCase


class ImplicitGrantTestCase(OAuthTestCase):

    def test_oauth_authorize_implicit(self):
        application = self.create_oauth_app()
        self.authorize_success_helper(application, "https://example.com/callback", True)

    def test_oauth_authorize_implicit_decline(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        query_string = {
            "client_id": application["client_id"],
            "response_type": "token",
            "scope": "profile",
            "state": "random-state",
            "redirect_uri": redirect_uri,
        }
        self.authorize_oauth_prompt_helper(query_string)

        with login_user(self.user2):
            response = self.client.post(
                "/oauth2/authorize/confirm",
                query_string=query_string,
                data={
                    "confirm": "no",
                    "csrf_token": g.csrf_token
                }
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, "https://example.com/callback?error=access_denied")

    def test_oauth_authorize_missing_client_id(self):
        application = self.create_oauth_app()
        query_string = {
            "response_type": "token",
            "scope": "profile",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback",
        }
        error = {"name": "invalid_client", "description": ""}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_authorize_invalid_client_id(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": "asb",
            "response_type": "token",
            "scope": "profile",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback",
        }
        error = {"name": "invalid_client", "description": ""}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_authorize_missing_response_type(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": application["client_id"],
            "scope": "profile",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback",
        }
        error = {"name": "unsupported_response_type", "description": "response_type=None is not supported"}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_authorize_invalid_response_type(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": application["client_id"],
            "response_type": "invalid",
            "scope": "profile",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback",
        }
        error = {"name": "unsupported_response_type", "description": "response_type=invalid is not supported"}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_authorize_missing_scope(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": application["client_id"],
            "response_type": "token",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback",
        }
        error = {"name": "invalid_scope", "description": "The requested scope is invalid, unknown, or malformed."}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_authorize_invalid_scope(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": application["client_id"],
            "response_type": "token",
            "scope": "test-scope-abc",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback",
        }
        error = {"name": "invalid_scope", "description": "The requested scope is invalid, unknown, or malformed."}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_authorize_missing_redirect_uri(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": application["client_id"],
            "response_type": "token",
            "scope": "profile",
            "state": "random-state",
        }
        error = {"name": "invalid_request", "description": "Missing \"redirect_uri\" in request."}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_authorize_invalid_redirect_uri(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": application["client_id"],
            "response_type": "token",
            "scope": "profile",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback2",
        }
        error = {"name": "invalid_request", "description": "Redirect URI https://example.com/callback2 is not supported by client."}
        self.authorize_error_helper(self.user2, query_string, error)

    @pytest.mark.skip
    def test_oauth_authorize_parameter_reuse(self):
        application = self.create_oauth_app()
        query_string = MultiDict([
            ("client_id", application["client_id"]),
            ("scope", "profile"),
            ("state", "random-state"),
            ("redirect_uri", "https://example.com/callback"),
            ("response_type", "token"),
            ("response_type", "token"),
        ])
        error = {"name": "invalid_request", "description": ""}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_authorize_cancel_url(self):
        application = self.create_oauth_app()
        with login_user(self.user2):
            response = self.client.get(
                "/oauth2/authorize",
                query_string={
                    "client_id": application["client_id"],
                    "response_type": "token",
                    "scope": "profile",
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
                "response_type": "token",
                "scope": "profile",
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
        self.assertEqual(unquote(fragment_args["returnto"][0]), f"http://localhost/oauth2/authorize?client_id={application['client_id']}&response_type=token&scope=profile&state=random-state&redirect_uri=https://example.com/callback")

    def test_oauth_authorize_multiple_redirect_uris(self):
        application = self.create_oauth_app(redirect_uris=[
            "https://example.com/callback1",
            "https://example.com/callback2"
        ])
        self.authorize_success_helper(application, "https://example.com/callback1")
        self.authorize_success_helper(application, "https://example.com/callback2", approval_prompt="force")

    def test_oauth_approval_prompt_auto_not_allowed_for_implicit(self):
        application = self.create_oauth_app(redirect_uris=[
            "https://example.com/callback1",
            "https://example.com/callback2"
        ])
        self.authorize_success_helper(application, "https://example.com/callback1")

        query_string = {
            "client_id": application["client_id"],
            "response_type": "token",
            "scope": "profile",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback2",
        }
        self.authorize_oauth_prompt_helper(query_string)

    def test_oauth_approval_prompt_force(self):
        redirect_uri1 = "https://example.com/callback1"
        redirect_uri2 = "https://example.com/callback2"
        application = self.create_oauth_app(redirect_uris=[
            "https://example.com/callback1",
            "https://example.com/callback2"
        ])
        self.authorize_success_helper(application, redirect_uri1)

        query_string = {
            "client_id": application["client_id"],
            "response_type": "token",
            "scope": "profile",
            "state": "random-state",
            "redirect_uri": redirect_uri2,
            "approval_prompt": "force",
        }
        self.authorize_oauth_prompt_helper(query_string)

    def test_oauth_approval_prompt_none(self):
        application = self.create_oauth_app(redirect_uris=[
            "https://example.com/callback1",
            "https://example.com/callback2"
        ])
        self.authorize_success_helper(application, "https://example.com/callback1")

        query_string = {
            "client_id": application["client_id"],
            "response_type": "token",
            "scope": "profile",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback2",
            "approval_prompt": "auto",
        }
        self.authorize_oauth_prompt_helper(query_string)

    def test_oauth_approval_prompt_invalid(self):
        application = self.create_oauth_app(redirect_uris=[
            "https://example.com/callback1",
            "https://example.com/callback2"
        ])
        query_string = {
            "client_id": application["client_id"],
            "response_type": "token",
            "scope": "profile",
            "state": "random-state",
            "redirect_uri": "https://example.com/callback2",
            "approval_prompt": "invalid",
        }
        error = {"name": "invalid_request", "description": "Invalid \"approval_prompt\" in request."}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_approval_prompt_scope_mismatch(self):
        redirect_uri1 = "https://example.com/callback1"
        redirect_uri2 = "https://example.com/callback2"
        application = self.create_oauth_app(redirect_uris=[redirect_uri1, redirect_uri2])
        self.authorize_success_helper(application, redirect_uri1)

        query_string = {
            "client_id": application["client_id"],
            "response_type": "token",
            "scope": "profile tag",
            "state": "random-state",
            "redirect_uri": redirect_uri2,
        }

        with login_user(self.user2):
            response = self.client.get("/oauth2/authorize", query_string=query_string)
            self.assertTemplateUsed("oauth/prompt.html")
            props = json.loads(self.get_context_variable("props"))

            self.assertEqual(props["client_name"], "test-client")
            self.assertEqual(props["scopes"], [
                {"name": "profile", "description": "View your public account information"},
                {"name": "tag", "description": "View and modify your private tags"},
            ])
            self.assertEqual(props["cancel_url"], redirect_uri2 + "?error=access_denied")
            self.assertEqual(props["csrf_token"], g.csrf_token)

            parsed = urlparse(props["submission_url"])
            self.assertEqual(parsed.path, "/oauth2/authorize/confirm")
            self.assertEqual(parse_qs(parsed.query), {k: [v] for k, v in query_string.items()})

    def test_oauth_authorize_implicit_form_post(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        query_string = {
            "client_id": application["client_id"],
            "response_type": "token",
            "scope": "profile",
            "state": "random-state",
            "redirect_uri": redirect_uri,
            "response_mode": "form_post"
        }

        self.authorize_oauth_prompt_helper(query_string)

        with login_user(self.user2):
            response = self.client.post("/oauth2/authorize/confirm", query_string=query_string, data={
                "confirm": "yes",
                "csrf_token": g.csrf_token
            })

            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed("oauth/authorize_form_post.html")
            self.assertEqual(self.get_context_variable("redirect_uri"), redirect_uri)

            fragment_args = self.get_context_variable("values")

            self.assertIsNone(fragment_args.get("error"))

            self.assertEqual(len(fragment_args["state"]), 1)
            self.assertEqual(fragment_args["state"][0], "random-state")

            self.assertEqual(len(fragment_args["token_type"]), 1)
            self.assertEqual(fragment_args["token_type"][0], "Bearer")

            self.assertEqual(len(fragment_args["expires_in"]), 1)
            self.assertEqual(fragment_args["expires_in"][0], "3600")

            self.assertEqual(len(fragment_args["access_token"]), 1)
            tokens = db.session.query(OAuth2AccessToken).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2AccessToken.client_id == OAuth2Client.id,
                OAuth2AccessToken.user_id == self.user2.id,
            ).all()
            tokens = {token.access_token for token in tokens}
            self.assertIn(fragment_args["access_token"][0], tokens)
            self.assertNotIn("refresh_token", fragment_args)
