from authlib.integrations.sqla_oauth2 import (
    create_query_client_func,
    create_save_token_func,
    create_revocation_endpoint
)
from authlib.integrations.flask_oauth2 import AuthorizationServer

from metabrainz.new_oauth.models import db
from metabrainz.new_oauth.models.client import OAuth2Client
from metabrainz.new_oauth.models.token import OAuth2Token, save_token

query_client = create_query_client_func(db.session, OAuth2Client)
revoke_token = create_revocation_endpoint(db.session, OAuth2Token)

# TODO: We can also configure the expiry time and token generation function
#  for the server. Its simple and will also be nice to prefix our tokens
#  with meb. Rationale: https://github.blog/2021-04-05-behind-githubs-new-authentication-token-formats/
authorization_server = AuthorizationServer(query_client=query_client, save_token=save_token)
