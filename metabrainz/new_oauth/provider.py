from authlib.integrations.sqla_oauth2 import (
    create_query_client_func,
    create_save_token_func
)
from authlib.integrations.flask_oauth2 import AuthorizationServer
from authlib.oauth2.rfc6749 import ImplicitGrant
from authlib.oauth2.rfc7636 import CodeChallenge

from metabrainz.new_oauth.authorization_grant import AuthorizationCodeGrant
from metabrainz.new_oauth.refresh_grant import RefreshTokenGrant
from metabrainz.new_oauth.models import db
from metabrainz.new_oauth.models.client import OAuth2Client
from metabrainz.new_oauth.models.token import OAuth2Token

query_client = create_query_client_func(db.session, OAuth2Client)
save_token = create_save_token_func(db.session, OAuth2Token)

# TODO: We can also configure the expiry time and token generation function
#  for the server. Its simple and will also be nice to prefix our tokens
#  with meb. Rationale: https://github.blog/2021-04-05-behind-githubs-new-authentication-token-formats/
authorization_server = AuthorizationServer(query_client=query_client, save_token=save_token)

authorization_server.register_grant(AuthorizationCodeGrant, [CodeChallenge(required=False)])
authorization_server.register_grant(ImplicitGrant)
authorization_server.register_grant(RefreshTokenGrant)
