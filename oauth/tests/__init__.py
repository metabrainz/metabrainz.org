import json
from contextlib import contextmanager
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs, urlencode

from flask import g
from flask_testing import TestCase
from sqlalchemy import delete

import oauth
from oauth.authorization_code_grant import AuthorizationCodeGrant
from oauth.login import User
from oauth.model import OAuth2Scope, db, OAuth2AccessToken, OAuth2RefreshToken, OAuth2Client, OAuth2AuthorizationCode
from oauth.refresh_grant import RefreshTokenGrant


@contextmanager
def login_user(user):
    try:
        g._login_user = user
        yield user
    finally:
        del g._login_user


class OAuthTestCase(TestCase):

    def create_app(self):
        app = oauth.create_app()
        app.config["TESTING"] = False
        app.config["DEBUG"] = False
        return app

    def setUp(self):
        self.user1 = User(user_id=1, user_name="test-user-1")
        self.user2 = User(user_id=2, user_name="test-user-2")

        scopes = [
            OAuth2Scope(name="test-scope-1", description="Test Scope 1"),
            OAuth2Scope(name="test-scope-2", description="Test Scope 2")
        ]
        db.session.add_all(scopes)
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

    def authorize_success_helper(self, application, redirect_uri, only_one_code=False, approval_prompt=None):
        query_string = {
            "client_id": application["client_id"],
            "response_type": "token",
            "scope": "test-scope-1",
            "state": "random-state",
            "redirect_uri": redirect_uri,
        }
        if approval_prompt is not None:
            query_string["approval_prompt"] = approval_prompt

        with login_user(self.user2):
            response = self.client.get("/oauth2/authorize", query_string=query_string)
            self.assertTemplateUsed("oauth/prompt.html")
            props = json.loads(self.get_context_variable("props"))
            self.assertEqual(props["client_name"], "test-client")
            self.assertEqual(props["scopes"], [{"name": "test-scope-1", "description": "Test Scope 1"}])
            self.assertEqual(props["cancel_url"], redirect_uri + "?error=access_denied")
            self.assertEqual(props["csrf_token"], g.csrf_token)

            parsed = urlparse(props["submission_url"])
            self.assertEqual(parsed.path, "/oauth2/authorize/confirm")
            self.assertEqual(parse_qs(parsed.query), {k: [v] for k, v in query_string.items()})

            response = self.client.post("/oauth2/authorize/confirm", query_string=query_string, data={
                "confirm": "yes",
                "csrf_token": g.csrf_token
            })
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.startswith(redirect_uri))
            parsed = urlparse(response.location)
            fragment_args = parse_qs(parsed.fragment)

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
            if only_one_code:
                self.assertEqual(len(tokens), 1)

    def authorize_success_for_token_grant_helper(self, application, redirect_uri,
                                                 only_one_code=False, approval_prompt=None):
        query_string = {
            "client_id": application["client_id"],
            "response_type": "code",
            "scope": "test-scope-1",
            "state": "random-state",
            "redirect_uri": redirect_uri,
        }
        if approval_prompt is not None:
            query_string["approval_prompt"] = approval_prompt
        with login_user(self.user2):
            response = self.client.get("/oauth2/authorize", query_string=query_string)
            self.assertTemplateUsed("oauth/prompt.html")
            props = json.loads(self.get_context_variable("props"))
            self.assertEqual(props["client_name"], "test-client")
            self.assertEqual(props["scopes"], [{"name": "test-scope-1", "description": "Test Scope 1"}])
            self.assertEqual(props["cancel_url"], redirect_uri + "?error=access_denied")
            self.assertEqual(props["csrf_token"], g.csrf_token)

            parsed = urlparse(props["submission_url"])
            self.assertEqual(parsed.path, "/oauth2/authorize/confirm")
            self.assertEqual(parse_qs(parsed.query), {k: [v] for k, v in query_string.items()})

            response = self.client.post("/oauth2/authorize/confirm", query_string=query_string, data={
                "confirm": "yes",
                "csrf_token": g.csrf_token
            })
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
                OAuth2AuthorizationCode.client_id == OAuth2Client.id,
                OAuth2AuthorizationCode.user_id == self.user2.id,
            ).all()
            codes = {code.code for code in codes}
            self.assertIn(query_args["code"][0], codes)
            if only_one_code:
                self.assertEqual(len(codes), 1)

            self.assertEqual(parsed.fragment, "_")
            return query_args["code"][0]

    def authorize_error_helper(self, user, query_string, error):
        with login_user(user):
            response = self.client.get(
                "/oauth2/authorize",
                query_string=query_string,
            )
            self.assertTemplateUsed("oauth/error.html")
            props = json.loads(self.get_context_variable("props"))
            self.assertEqual(props["error"], error)

            response = self.client.post(
                "/oauth2/authorize/confirm",
                query_string=query_string,
                data={
                    "confirm": "yes",
                    "csrf_token": g.csrf_token
                }
            )
            self.assertTemplateUsed("oauth/error.html")
            props = json.loads(self.get_context_variable("props"))
            self.assertEqual(props["error"], error)

    def token_success_token_grant_helper(self, application, code, redirect_uri, only_one_token=False):
        with patch("oauth.login.load_user_from_db", return_value=self.user2):
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
            self.assertEqual(data["expires_in"], 3600)
            self.assertEqual(data["token_type"], "Bearer")

            access_tokens = db.session.query(OAuth2AccessToken).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2AccessToken.client_id == OAuth2Client.id,
                OAuth2AccessToken.user_id == self.user2.id,
            ).all()
            access_tokens = {token.access_token for token in access_tokens}
            self.assertIn(data["access_token"], access_tokens)

            refresh_tokens = db.session.query(OAuth2RefreshToken).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2RefreshToken.client_id == OAuth2Client.id,
                OAuth2RefreshToken.user_id == self.user2.id,
            ).all()
            refresh_tokens = {token.refresh_token for token in refresh_tokens}
            self.assertIn(data["refresh_token"], refresh_tokens)

            if only_one_token:
                self.assertEqual(len(access_tokens), 1)
                self.assertEqual(len(refresh_tokens), 1)

            return data

    def refresh_grant_success_helper(self, application, token):
        with patch("oauth.login.load_user_from_db", return_value=self.user2):
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
                OAuth2AccessToken.client_id == OAuth2Client.id,
                OAuth2AccessToken.user_id == self.user2.id,
                OAuth2AccessToken.revoked.is_(False),
            ).all()
            access_tokens = {token.access_token for token in access_tokens}
            self.assertIn(new_token["access_token"], access_tokens)

            refresh_tokens = db.session.query(OAuth2RefreshToken).join(OAuth2Client).filter(
                OAuth2Client.client_id == application["client_id"],
                OAuth2RefreshToken.client_id == OAuth2Client.id,
                OAuth2RefreshToken.user_id == self.user2.id,
                OAuth2RefreshToken.revoked.is_(False),
            ).all()
            refresh_tokens = {token.refresh_token for token in refresh_tokens}
            self.assertIn(new_token["refresh_token"], refresh_tokens)
            return token

    def introspection_success_helper(self, data):
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
            self.assertEqual(response.json["expires_at"] - response.json["issued_at"], 3600)
