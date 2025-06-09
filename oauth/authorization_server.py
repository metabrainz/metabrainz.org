from urllib.parse import urlparse, urlunparse

from authlib.integrations.flask_oauth2 import AuthorizationServer
from authlib.integrations.sqla_oauth2 import (
    create_query_client_func,
)
from authlib.oauth2.rfc6749 import InvalidScopeError, scope_to_list
from authlib.oauth2.rfc7636 import CodeChallenge

from oauth.authorization_code_grant import AuthorizationCodeGrant
from oauth.client_credentials import ClientCredentialsGrant
from oauth.implicit_grant import ImplicitGrant
from oauth.introspection import OAuth2IntrospectionEndpoint
from oauth.model import db, OAuth2Scope
from oauth.model.base_token import save_token
from oauth.model.client import OAuth2Client
from oauth.refresh_grant import RefreshTokenGrant
from oauth.revocation import OAuth2RevocationEndpoint

query_client = create_query_client_func(db.session, OAuth2Client)


class CustomAuthorizationServer(AuthorizationServer):

    def validate_requested_scope(self, scope, state=None):
        if not scope:
            raise InvalidScopeError(state=state)

        all_scopes = db.session.query(OAuth2Scope).all()
        all_scopes = {s.name for s in all_scopes}
        scopes = set(scope_to_list(scope))
        if not all_scopes.issuperset(scopes):
            raise InvalidScopeError(state=state)

    def handle_response(self, status_code, payload, headers):
        # add arbitrary fragment to redirect uri
        # (for rationale: see https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics#section-4.1.3)
        response = super().handle_response(status_code, payload, headers)
        if response.headers.get("Location"):
            scheme, netloc, path, params, query, fragment = urlparse(response.headers["Location"])
            if not fragment:
                fragment = "_"
            response.headers.set("Location", urlunparse((scheme, netloc, path, params, query, fragment)))
        return response


# TODO: configure the expiry time for tokens
authorization_server = CustomAuthorizationServer(query_client=query_client, save_token=save_token)
authorization_server.register_grant(AuthorizationCodeGrant, [CodeChallenge(required=False)])
authorization_server.register_grant(ImplicitGrant)
authorization_server.register_grant(RefreshTokenGrant)
authorization_server.register_grant(ClientCredentialsGrant)
authorization_server.register_endpoint(OAuth2RevocationEndpoint)
authorization_server.register_endpoint(OAuth2IntrospectionEndpoint)
