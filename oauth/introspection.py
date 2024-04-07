from authlib.oauth2.rfc7662 import IntrospectionEndpoint

from oauth import login
from oauth.model import db
from oauth.model.token import OAuth2Token


class OAuth2IntrospectionEndpoint(IntrospectionEndpoint):

    CLIENT_AUTH_METHODS = ["client_secret_post"]

    def query_token(self, token_str, token_type_hint):
        base_query = db.session.query(OAuth2Token)
        if token_type_hint == "access_token":
            token = base_query.filter_by(access_token=token_str).first()
        elif token_type_hint == "refresh_token":
            token = base_query.filter_by(refresh_token=token_str).first()
        else:  # without token_type_hint
            token = base_query.filter_by(access_token=token_str).first()
            if not token:
                token = base_query.filter_by(refresh_token=token_str).first()
        return token

    def introspect_token(self, token):
        user = login.load_user_from_db(token.user_id)
        return {
            "client_id": token.client.client_id,
            "token_type": "Bearer",
            "metabrainz_user_id": token.user_id,
            "scope": token.get_scope(),
            "sub": user.user_name,
            "issued_by": "https://metabrainz.org/",
            "expires_at": int(token.get_expires_at().timestamp()),
            "issued_at": int(token.issued_at.timestamp()),
        }

    def check_permission(self, token, client, request):
        return token.client_id == client.id
