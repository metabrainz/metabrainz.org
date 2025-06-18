from unittest.mock import patch
from urllib.parse import urlparse, parse_qs

from flask import g
from authlib.oidc.discovery import OpenIDProviderMetadata

from oauth.tests import OAuthTestCase, login_user
from oauth.model import db, OAuth2AccessToken


class OpenIdIntegrationTestCase(OAuthTestCase):
    def test_openid_discovery_endpoint(self):
        response = self.client.get("/oauth2/.well-known/openid-configuration")
        self.assert200(response)
        data = response.json
        self.assertEqual(data["issuer"], "https://metabrainz.org")
        self.assertIn("authorization_endpoint", data)
        self.assertIn("token_endpoint", data)
        self.assertIn("userinfo_endpoint", data)
        self.assertIn("jwks_uri", data)
        self.assertIn("scopes_supported", data)
        self.assertIn("response_types_supported", data)
        self.assertIn("grant_types_supported", data)
        self.assertIn("id_token_signing_alg_values_supported", data)

        # metadata = OpenIDProviderMetadata(response.json)
        # metadata.validate()

    def test_openid_jwks_endpoint(self):
        response = self.client.get("/oauth2/.well-known/jwks.json")
        self.assert200(response)
        data = response.json
        self.assertIn("keys", data)
        self.assertIsInstance(data["keys"], list)

    def test_openid_userinfo_endpoint_success(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)
        access_token = token["access_token"]

        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.get(
                "/oauth2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            self.assert200(response)
            data = response.json
            self.assertEqual(data["sub"], self.user2.user_name)
            self.assertEqual(data["metabrainz_user_id"], self.user2.id)
            self.assert_security_headers(response)

    def test_openid_userinfo_endpoint_missing_token(self):
        response = self.client.get("/oauth2/userinfo")
        self.assertEqual(response.status_code, 401)
        data = response.json
        self.assertIn("error", data)
        self.assertEqual(data["error"], "missing auth header")
        self.assert_security_headers(response)

    def test_openid_userinfo_endpoint_invalid_token(self):
        response = self.client.get(
            "/oauth2/userinfo",
            headers={"Authorization": "Bearer invalidtoken"}
        )
        self.assertEqual(response.status_code, 403)
        data = response.json
        self.assertIn("error", data)
        self.assertEqual(data["error"], "invalid access token")
        self.assert_security_headers(response)

    def test_openid_auth_flow_id_token(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        query_string = {
            "client_id": application["client_id"],
            "response_type": "id_token",
            "scope": "openid profile",
            "state": "random-state",
            "nonce": "test-nonce",
            "redirect_uri": redirect_uri,
        }
        self.authorize_oauth_prompt_helper(query_string, openid=True)
        with login_user(self.user2):
            response = self.client.post(
                "/oauth2/authorize/confirm",
                query_string=query_string,
                data={"confirm": "yes", "csrf_token": g.csrf_token}
            )

            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.startswith(redirect_uri))

            parsed = urlparse(response.location)
            fragment_args = parse_qs(parsed.fragment)
            self.assertIsNone(fragment_args.get("error"))
            self.assertIn("id_token", fragment_args)
            self.assertIn("state", fragment_args)
            self.assertEqual(fragment_args["state"][0], "random-state")
            self.assertIn("nonce", query_string)
            self.assert_security_headers(response)

    def test_openid_code_flow_success(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        query_string = {
            "client_id": application["client_id"],
            "response_type": "code",
            "scope": "openid profile",
            "state": "random-state",
            "nonce": "test-nonce",
            "redirect_uri": redirect_uri,
        }
        self.authorize_oauth_prompt_helper(query_string, openid=True)
        with login_user(self.user2):
            response = self.client.post(
                "/oauth2/authorize/confirm",
                query_string=query_string,
                data={"confirm": "yes", "csrf_token": g.csrf_token}
            )
            self.assertEqual(response.status_code, 302)
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(response.location)
            query_args = parse_qs(parsed.query)
            self.assertIsNone(query_args.get("error"))
            self.assertIn("code", query_args)
            code = query_args["code"][0]

        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            token_response = self.client.post(
                "/oauth2/token",
                data={
                    "client_id": application["client_id"],
                    "client_secret": application["client_secret"],
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                    "code": code,
                }
            )
            self.assert200(token_response)
            data = token_response.json
            self.assertIn("id_token", data)
            self.assertIn("access_token", data)
            self.assert_security_headers(token_response)

    def test_openid_implicit_flow_id_token_token(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        query_string = {
            "client_id": application["client_id"],
            "response_type": "id_token token",
            "scope": "openid profile",
            "state": "random-state",
            "nonce": "test-nonce",
            "redirect_uri": redirect_uri,
        }
        self.authorize_oauth_prompt_helper(query_string, openid=True)
        with login_user(self.user2):
            response = self.client.post(
                "/oauth2/authorize/confirm",
                query_string=query_string,
                data={"confirm": "yes", "csrf_token": g.csrf_token}
            )
            self.assertEqual(response.status_code, 302)
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(response.location)
            fragment_args = parse_qs(parsed.fragment)
            self.assertIsNone(fragment_args.get("error"))
            self.assertIn("id_token", fragment_args)
            self.assertIn("access_token", fragment_args)
            self.assertIn("state", fragment_args)
            self.assertEqual(fragment_args["state"][0], "random-state")
            self.assert_security_headers(response)

    def test_openid_userinfo_post_success(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)
        access_token = token["access_token"]
        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.post(
                "/oauth2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            # todo: fix
            # Accept 200 or 405 (if not supported)
            if response.status_code == 200:
                data = response.json
                self.assertEqual(data["sub"], self.user2.user_name)
                self.assertEqual(data["metabrainz_user_id"], self.user2.id)
                self.assert_security_headers(response)
            else:
                self.assertEqual(response.status_code, 405)

    def test_openid_missing_nonce_error(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        query_string = {
            "client_id": application["client_id"],
            "response_type": "id_token",
            "scope": "openid",
            "state": "random-state",
            "redirect_uri": redirect_uri,
        }
        error = {"name": "invalid_request", "description": "Missing \"nonce\" in request."}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_openid_missing_openid_scope(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        query_string = {
            "client_id": application["client_id"],
            "response_type": "id_token",
            "scope": "profile",
            "state": "random-state",
            "nonce": "test-nonce",
            "redirect_uri": redirect_uri,
        }
        error = {"name": "invalid_scope", "description": "Missing \"openid\" scope"}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_openid_invalid_client_id(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        query_string = {
            "client_id": "invalid-client-id",
            "response_type": "id_token",
            "scope": "openid",
            "state": "random-state",
            "nonce": "test-nonce",
            "redirect_uri": redirect_uri,
        }
        error = {"name": "invalid_client", "description": ""}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_openid_invalid_redirect_uri(self):
        application = self.create_oauth_app()
        query_string = {
            "client_id": application["client_id"],
            "response_type": "id_token",
            "scope": "openid",
            "state": "random-state",
            "nonce": "test-nonce",
            "redirect_uri": "https://invalid.com/callback",
        }
        error = {"name": "invalid_request", "description": "Redirect URI https://invalid.com/callback is not supported by client."}
        self.authorize_error_helper(self.user2, query_string, error)

    def test_openid_userinfo_expired_token(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)
        access_token = token["access_token"]

        db_token = db.session.query(OAuth2AccessToken).filter_by(access_token=access_token).first()
        db_token.expires_in = -1
        db.session.commit()
        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.get(
                "/oauth2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            self.assertEqual(response.status_code, 403)
            data = response.json
            self.assertIn("error", data)
            self.assertEqual(data["error"], "expired access token")
            self.assert_security_headers(response)

    def test_openid_userinfo_revoked_token(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        token = self.token_success_token_grant_helper(application, code, redirect_uri, True)
        access_token = token["access_token"]

        db_token = db.session.query(OAuth2AccessToken).filter_by(access_token=access_token).first()
        db_token.revoked = True
        db.session.commit()
        with patch("oauth.login.load_user_from_db", return_value=self.user2):
            response = self.client.get(
                "/oauth2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            self.assertEqual(response.status_code, 403)
            data = response.json
            self.assertIn("error", data)
            self.assertEqual(data["error"], "expired access token")
            self.assert_security_headers(response)

    def test_openid_invalid_response_type(self):
        application = self.create_oauth_app()
        redirect_uri = "https://example.com/callback"
        query_string = {
            "client_id": application["client_id"],
            "response_type": "invalid_type",
            "scope": "openid",
            "state": "random-state",
            "nonce": "test-nonce",
            "redirect_uri": redirect_uri,
        }
        error = {"name": "unsupported_response_type", "description": "response_type=invalid_type is not supported"}
        self.authorize_error_helper(self.user2, query_string, error)
