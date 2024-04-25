import base64
import hashlib
import json
import uuid
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs

import pytest
from flask import g

from oauth.authorization_code_grant import AuthorizationCodeGrant
from oauth.model import db, OAuth2Client, OAuth2AccessToken, OAuth2AuthorizationCode, OAuth2RefreshToken
from oauth.tests import login_user, OAuthTestCase


class AuthorizationCodeGrantPKCETestCase(OAuthTestCase):

    def _test_oauth_authorize_success_helper(self, application, redirect_uri, code_challenge,
                                             code_challenge_method, only_one_code=False):
        query_string = {
            "client_id": application["client_id"],
            "response_type": "code",
            "scope": "test-scope-1",
            "state": "random-state",
            "code_challenge": code_challenge,
            "redirect_uri": redirect_uri,
        }
        if code_challenge_method:
            query_string["code_challenge_method"] = code_challenge_method

        self.authorize_oauth_prompt_helper(query_string)

        with login_user(self.user2):
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

            self.assertIsNone(query_args.get("code_challenge"))
            self.assertIsNone(query_args.get("code_challenge_method"))

            return query_args["code"][0]

    def _test_oauth_token_success_helper(self, application, code, code_verifier, redirect_uri, only_one_token=False):
        with patch.object(
            AuthorizationCodeGrant,
            "authenticate_user",
            return_value=self.user2
        ):
            response = self.client.post(
                "/oauth2/token",
                data={
                    "client_id": application["client_id"],
                    "client_secret": application["client_secret"],
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                    "code_verifier": code_verifier,
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

    def generate_s256_code_challenge(self, code_challenge_method):
        code_verifier = str(uuid.uuid4()) + str(uuid.uuid4()) + str(uuid.uuid4())
        if code_challenge_method == "S256":
            hashed = hashlib.sha256(code_verifier.encode("ascii")).digest()
            code_challenge = base64.urlsafe_b64encode(hashed).decode("utf-8").rstrip("=")
        else:
            code_challenge = code_verifier
        return code_verifier, code_challenge

    def test_oauth_pkce_s256_success(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        code_challenge_method = "S256"
        code_verifier, code_challenge = self.generate_s256_code_challenge(code_challenge_method)

        code = self._test_oauth_authorize_success_helper(application, redirect_uri, code_challenge,
                                                         code_challenge_method, only_one_code=True)
        self._test_oauth_token_success_helper(application, code, code_verifier, redirect_uri, True)

    def test_oauth_pkce_plain_success(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        code_challenge_method = "plain"
        code_verifier, code_challenge = self.generate_s256_code_challenge(code_challenge_method)

        code = self._test_oauth_authorize_success_helper(application, redirect_uri, code_challenge,
                                                         code_challenge_method, only_one_code=True)
        self._test_oauth_token_success_helper(application, code, code_verifier, redirect_uri, True)

    def _test_oauth_token_error_helper(self, data, error):
        with patch.object(AuthorizationCodeGrant, "authenticate_user", return_value=self.user2):
            response = self.client.post("/oauth2/token", data=data)
            self.assert400(response)
            self.assertEqual(response.json, error)

    def test_oauth_pkce_missing_code_challenge(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        for code_challenge_method in ["plain", "S256"]:
            code_verifier, code_challenge = self.generate_s256_code_challenge(code_challenge_method)

            query_string = {
                "client_id": application["client_id"],
                "response_type": "code",
                "scope": "test-scope-1",
                "state": "random-state",
                "code_challenge_method": code_challenge_method,
                "redirect_uri": redirect_uri,
            }
            error = {"name": "invalid_request", "description": "Missing \"code_challenge\""}
            self.authorize_error_helper(self.user2, query_string, error)

    @pytest.mark.skip
    def test_oauth_pkce_invalid_code_challenge(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        for code_challenge_method in ["plain", "S256"]:
            code_verifier, code_challenge = self.generate_s256_code_challenge(code_challenge_method)

            query_string = {
                "client_id": application["client_id"],
                "response_type": "code",
                "scope": "test-scope-1",
                "state": "random-state",
                "code_challenge": "abc",
                "code_challenge_method": code_challenge_method,
                "redirect_uri": redirect_uri,
            }
            error = {}
            self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_pkce_missing_code_challenge_method(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        code_challenge_method = "plain"
        code_verifier, code_challenge = self.generate_s256_code_challenge(code_challenge_method)

        code = self._test_oauth_authorize_success_helper(application, redirect_uri, code_challenge,
                                                         None, only_one_code=True)
        self._test_oauth_token_success_helper(application, code, code_verifier, redirect_uri, True)

    def test_oauth_pkce_invalid_code_challenge_method(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        for code_challenge_method in ["plain", "S256"]:
            code_verifier, code_challenge = self.generate_s256_code_challenge(code_challenge_method)

            query_string = {
                "client_id": application["client_id"],
                "response_type": "code",
                "scope": "test-scope-1",
                "state": "random-state",
                "code_challenge": code_challenge,
                "code_challenge_method": "md5",
                "redirect_uri": redirect_uri,
            }
            error = {"description": "Unsupported \"code_challenge_method\"", "name": "invalid_request"}
            self.authorize_error_helper(self.user2, query_string, error)

    def test_oauth_pkce_missing_code_verifier(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        for code_challenge_method in ["plain", "S256"]:
            code_verifier, code_challenge = self.generate_s256_code_challenge(code_challenge_method)

            code = self._test_oauth_authorize_success_helper(application, redirect_uri, code_challenge,
                                                             code_challenge_method, only_one_code=False)

            data = {
                "client_id": application["client_id"],
                "client_secret": application["client_secret"],
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code": code,
            }
            error = {"error": "invalid_request", "error_description": "Missing \"code_verifier\""}
            self._test_oauth_token_error_helper(data, error)

    def test_oauth_pkce_invalid_code_verifier(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"

        for code_challenge_method in ["plain", "S256"]:
            code_verifier, code_challenge = self.generate_s256_code_challenge(code_challenge_method)

            code = self._test_oauth_authorize_success_helper(application, redirect_uri, code_challenge,
                                                             code_challenge_method, only_one_code=False)

            data = {
                "client_id": application["client_id"],
                "client_secret": application["client_secret"],
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code": code,
                "code_verifier": code_verifier + code_verifier,
            }
            error = {"error": "invalid_request", "error_description": "Invalid \"code_verifier\""}
            self._test_oauth_token_error_helper(data, error)
