from authlib.integrations.flask_oauth2 import AuthorizationServer
from authlib.integrations.sqla_oauth2 import (
    create_query_client_func,
    create_revocation_endpoint
)
from authlib.oauth2.rfc6749 import ImplicitGrant
from authlib.oauth2.rfc7636 import CodeChallenge

from metabrainz.model import db
from metabrainz.model.oauth.client import OAuth2Client
from metabrainz.model.oauth.token import OAuth2Token, save_token
from metabrainz.oauth.authorization_grant import AuthorizationCodeGrant
from metabrainz.oauth.introspection import OAuth2IntrospectionEndpoint
from metabrainz.oauth.refresh_grant import RefreshTokenGrant

query_client = create_query_client_func(db.session, OAuth2Client)
revoke_token = create_revocation_endpoint(db.session, OAuth2Token)

# TODO: We can also configure the expiry time and token generation function
#  for the server. Its simple and will also be nice to prefix our tokens
#  with meb. Rationale: https://github.blog/2021-04-05-behind-githubs-new-authentication-token-formats/
authorization_server = AuthorizationServer(query_client=query_client, save_token=save_token)
authorization_server.register_grant(AuthorizationCodeGrant, [CodeChallenge(required=False)])
authorization_server.register_grant(ImplicitGrant)
authorization_server.register_grant(RefreshTokenGrant)
authorization_server.register_endpoint(revoke_token)
authorization_server.register_endpoint(OAuth2IntrospectionEndpoint)
