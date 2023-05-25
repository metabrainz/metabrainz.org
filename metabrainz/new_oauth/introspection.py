from authlib.oauth2.rfc7662 import IntrospectionEndpoint

from metabrainz.model import db
from metabrainz.new_oauth.models.token import OAuth2Token


class OAuth2IntrospectionEndpoint(IntrospectionEndpoint):

    def query_token(self, token_str, token_type_hint, client):
        base_query = db.session.query(OAuth2Token)
        if token_type_hint == 'access_token':
            token = base_query.filter_by(access_token=token_str).first()
        elif token_type_hint == 'refresh_token':
            token = base_query.filter_by(refresh_token=token_str).first()
        else:  # without token_type_hint
            token = base_query.filter_by(access_token=token_str).first()
            if not token:
                token = base_query.filter_by(refresh_token=token_str).first()
        return token

    def introspect_token(self, token):
        return {
            'active': True,
            'client_id': token.client.client_id,
            'token_type': 'Bearer',
            'username': token.user.name,
            'metabrainz_user_id': token.user_id,
            'scope': token.get_scope(),
            'sub': token.user.name,
            'aud': token.client.client_id,
            'iss': 'https://metabrainz.com/',
            'exp': int(token.get_expires_at().timestamp()),
            'iat': int(token.issued_at.timestamp()),
        }

    def check_permission(self, token, client, request):
        # TODO: discuss restricting
        return True
