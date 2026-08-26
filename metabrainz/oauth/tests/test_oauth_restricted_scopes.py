import json
from urllib.parse import urlparse, parse_qs

from flask import g, url_for

from metabrainz.admin.views import OAuth2ClientModelView, RestrictedScopeField
from metabrainz.model import db, OAuth2Client, OAuth2Scope, OAuth2AccessToken
from metabrainz.model.oauth.client import OAuth2ClientPrivilege
from metabrainz.oauth.tests import OAuthTestCase

RESTRICTED_SCOPE = "musicbrainz:submit_isrc"
REDIRECT_URI = "https://example.com/callback"


class RestrictedScopesTestCase(OAuthTestCase):

    def _get_client(self, application):
        return db.session.query(OAuth2Client).filter_by(client_id=application["client_id"]).first()

    def _authorization_query(self, application, response_type, scope):
        return {
            "client_id": application["client_id"],
            "response_type": response_type,
            "scope": scope,
            "state": "random-state",
            "redirect_uri": REDIRECT_URI,
        }

    def _confirm_authorization(self, query_string):
        self.client.get("/oauth2/authorize", query_string=query_string)
        return self.client.post("/oauth2/authorize/confirm", query_string=query_string, data={
            "confirm": "yes",
            "csrf_token": g.csrf_token,
        })

    def _access_token_scopes(self, access_token):
        token = db.session.query(OAuth2AccessToken).filter_by(access_token=access_token).first()
        return {scope.name for scope in token.scopes}

    def test_disallowed_scopes(self):
        application = self.create_oauth_app()
        client = self._get_client(application)

        # nothing is restricted to begin with
        self.assertEqual(client.disallowed_scopes(f"profile {RESTRICTED_SCOPE}"), [])
        self.assertEqual(
            client.get_allowed_scope(f"profile {RESTRICTED_SCOPE}"),
            f"profile {RESTRICTED_SCOPE}",
        )

        self.restrict_scope(RESTRICTED_SCOPE)
        self.assertEqual(client.disallowed_scopes(f"profile {RESTRICTED_SCOPE}"), [RESTRICTED_SCOPE])
        self.assertEqual(client.disallowed_scopes("profile"), [])
        self.assertIsNone(client.get_allowed_scope(f"profile {RESTRICTED_SCOPE}"))
        self.assertEqual(client.get_allowed_scope("profile"), "profile")

        self.grant_scopes(application, RESTRICTED_SCOPE)
        client = self._get_client(application)
        self.assertEqual(client.disallowed_scopes(f"profile {RESTRICTED_SCOPE}"), [])
        self.assertEqual(
            client.get_allowed_scope(f"profile {RESTRICTED_SCOPE}"),
            f"profile {RESTRICTED_SCOPE}",
        )

        # the grant only covers the client it was made for
        other_client = self._get_client(self.create_oauth_app(owner=self.user2))
        self.assertEqual(other_client.disallowed_scopes(RESTRICTED_SCOPE), [RESTRICTED_SCOPE])

    def test_authorize_rejects_restricted_scope(self):
        application = self.create_oauth_app()
        self.restrict_scope(RESTRICTED_SCOPE)

        self.temporary_login(self.user2)
        query_string = self._authorization_query(application, "code", f"profile {RESTRICTED_SCOPE}")
        error = {
            "name": "invalid_scope",
            "description": f"The client is not allowed to request the following scopes: {RESTRICTED_SCOPE}",
        }
        self.authorize_error_helper(self.user2, query_string, error)

    def test_authorize_rejects_restricted_scope_for_implicit_grant(self):
        application = self.create_oauth_app()
        self.restrict_scope(RESTRICTED_SCOPE)

        self.temporary_login(self.user2)
        query_string = self._authorization_query(application, "token", RESTRICTED_SCOPE)
        error = {
            "name": "invalid_scope",
            "description": f"The client is not allowed to request the following scopes: {RESTRICTED_SCOPE}",
        }
        self.authorize_error_helper(self.user2, query_string, error)

    def test_authorize_allows_restricted_scope_for_granted_client(self):
        application = self.create_oauth_app()
        self.restrict_scope(RESTRICTED_SCOPE)
        self.grant_scopes(application, RESTRICTED_SCOPE)

        self.temporary_login(self.user2)
        query_string = self._authorization_query(application, "code", f"profile {RESTRICTED_SCOPE}")

        self.client.get("/oauth2/authorize", query_string=query_string)
        self.assertTemplateUsed("oauth/prompt.html")
        props = json.loads(self.get_context_variable("props"))
        self.assertIn(RESTRICTED_SCOPE, [scope["name"] for scope in props["scopes"]])

        response = self._confirm_authorization(query_string)
        self.assertEqual(response.status_code, 302)
        code = parse_qs(urlparse(response.location).query)["code"][0]

        response = self.client.post("/oauth2/token", data={
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code": code,
        })
        self.assert200(response)
        self.assertEqual(
            self._access_token_scopes(response.json["access_token"]),
            {"profile", RESTRICTED_SCOPE},
        )

    def test_unrestricted_scope_is_unaffected(self):
        application = self.create_oauth_app()
        self.restrict_scope(RESTRICTED_SCOPE)

        self.temporary_login(self.user2)
        query_string = self._authorization_query(application, "code", "profile")
        response = self._confirm_authorization(query_string)
        self.assertEqual(response.status_code, 302)
        self.assertIn("code", parse_qs(urlparse(response.location).query))

    def test_client_credentials_rejects_restricted_scope(self):
        application = self.create_oauth_app(privileges=[OAuth2ClientPrivilege.CLIENT_CREDENTIALS])
        self.restrict_scope(RESTRICTED_SCOPE)

        data = {
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "client_credentials",
            "scope": RESTRICTED_SCOPE,
        }
        response = self.client.post("/oauth2/token", data=data)
        self.assert400(response)
        self.assertEqual(response.json["error"], "invalid_scope")
        self.assertEqual(
            response.json["error_description"],
            f"The client is not allowed to request the following scopes: {RESTRICTED_SCOPE}",
        )

        self.grant_scopes(application, RESTRICTED_SCOPE)
        response = self.client.post("/oauth2/token", data=data)
        self.assert200(response)
        self.assertEqual(self._access_token_scopes(response.json["access_token"]), {RESTRICTED_SCOPE})

    def test_refresh_token_rejected_after_grant_is_withdrawn(self):
        application = self.create_oauth_app()
        self.restrict_scope(RESTRICTED_SCOPE)
        self.grant_scopes(application, RESTRICTED_SCOPE)

        self.temporary_login(self.user2)
        query_string = self._authorization_query(application, "code", f"profile {RESTRICTED_SCOPE}")
        response = self._confirm_authorization(query_string)
        code = parse_qs(urlparse(response.location).query)["code"][0]

        response = self.client.post("/oauth2/token", data={
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code": code,
        })
        self.assert200(response)
        refresh_token = response.json["refresh_token"]

        # the refresh token grant does not revalidate the requested scope, the client
        # must still stop getting tokens for the scope once the grant is withdrawn
        self.grant_scopes(application)
        response = self.client.post("/oauth2/token", data={
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        })
        self.assert400(response)
        self.assertEqual(response.json["error"], "invalid_scope")

        # the whole request is refused, the client has to narrow it down to the
        # scopes it may still request (or have the user authorize it again)
        response = self.client.post("/oauth2/token", data={
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": "profile",
        })
        self.assert200(response)
        self.assertEqual(self._access_token_scopes(response.json["access_token"]), {"profile"})

    def test_connect_services_scope_ships_restricted(self):
        scope = db.session.query(OAuth2Scope).filter_by(name="listenbrainz:connect-services").first()
        self.assertIsNotNone(scope)
        self.assertTrue(scope.restricted)

        application = self.create_oauth_app()
        self.temporary_login(self.user2)
        query_string = self._authorization_query(application, "code", "listenbrainz:connect-services")
        error = {
            "name": "invalid_scope",
            "description": "The client is not allowed to request the following scopes:"
                           " listenbrainz:connect-services",
        }
        self.authorize_error_helper(self.user2, query_string, error)

        response = self.client.get("/.well-known/openid-configuration")
        self.assert200(response)
        self.assertNotIn("listenbrainz:connect-services", response.json["scopes_supported"])

    def test_restricted_scopes_are_not_advertised(self):
        response = self.client.get("/.well-known/openid-configuration")
        self.assert200(response)
        self.assertIn(RESTRICTED_SCOPE, response.json["scopes_supported"])

        self.restrict_scope(RESTRICTED_SCOPE)
        response = self.client.get("/.well-known/openid-configuration")
        self.assert200(response)
        self.assertNotIn(RESTRICTED_SCOPE, response.json["scopes_supported"])
        self.assertIn("profile", response.json["scopes_supported"])

    def test_restricted_scope_field_roundtrip(self):
        application = self.create_oauth_app()
        client = self._get_client(application)
        scope = self.restrict_scope(RESTRICTED_SCOPE)
        form_class = OAuth2ClientModelView(db.session).get_form()

        form = form_class(meta={"csrf": False}, obj=client)
        field = form.restricted_scopes
        self.assertIsInstance(field, RestrictedScopeField)
        # only restricted scopes can be granted
        self.assertIn((scope.id, RESTRICTED_SCOPE), field.choices)
        self.assertNotIn("profile", [name for _, name in field.choices])
        self.assertEqual(field.data, [])

        field.data = [scope.id]
        form.populate_obj(client)
        db.session.commit()
        self.assertEqual([s.name for s in client.restricted_scopes], [RESTRICTED_SCOPE])

        # an empty selection withdraws the grant
        form = form_class(meta={"csrf": False}, obj=client)
        self.assertEqual(form.restricted_scopes.data, [scope.id])
        form.restricted_scopes.data = []
        form.populate_obj(client)
        db.session.commit()
        self.assertEqual(client.restricted_scopes, [])

    def test_restricted_scope_field_keeps_scopes_that_are_no_longer_restricted(self):
        application = self.create_oauth_app()
        scope = self.restrict_scope(RESTRICTED_SCOPE)
        self.grant_scopes(application, RESTRICTED_SCOPE)
        client = self._get_client(application)

        scope.restricted = False
        db.session.commit()

        form = OAuth2ClientModelView(db.session).get_form()(meta={"csrf": False}, obj=client)
        self.assertEqual(form.restricted_scopes.data, [scope.id])
        self.assertIn(
            (scope.id, f"{RESTRICTED_SCOPE} (no longer restricted)"),
            form.restricted_scopes.choices,
        )

    def test_admin_list_view_shows_restricted_scopes(self):
        application = self.create_oauth_app()
        self.restrict_scope(RESTRICTED_SCOPE)
        self.grant_scopes(application, RESTRICTED_SCOPE)

        self.app.config["ADMINS"] = [self.user1.name]
        self.temporary_login(self.user1)

        response = self.client.get(url_for("oauth-clients-admin.index_view"))
        self.assert200(response)
        self.assertIn(RESTRICTED_SCOPE, response.get_data(as_text=True))

    def test_admin_client_form_grants_restricted_scope(self):
        application = self.create_oauth_app()
        client = self._get_client(application)
        scope = self.restrict_scope(RESTRICTED_SCOPE)

        self.app.config["ADMINS"] = [self.user1.name]
        self.temporary_login(self.user1)
        url = url_for("oauth-clients-admin.edit_view", id=client.id)
        response = self.client.get(url)
        self.assert200(response)
        form = self.get_context_variable("form")

        response = self.client.post(url, data={
            "csrf_token": form.csrf_token.current_token,
            "name": client.name,
            "description": client.description,
            "website": client.website,
            "redirect_uris": "\n".join(client.redirect_uris),
            "privileges": [],
            "restricted_scopes": [str(scope.id)],
        })
        self.assertStatus(response, 302)
        db.session.refresh(client)
        self.assertEqual([s.name for s in client.restricted_scopes], [RESTRICTED_SCOPE])
