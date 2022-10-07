from authlib.oauth2.rfc7662 import IntrospectionEndpoint

from metabrainz.new_oauth.models import db
from metabrainz.new_oauth.models.token import OAuth2Token


class OAuth2IntrospectionEndpoint(IntrospectionEndpoint):

    def query_token(self, token, token_type_hint):
        base_query = db.session.query(OAuth2Token)
        if token_type_hint == 'access_token':
            token = base_query.filter_by(access_token=token).first()
        elif token_type_hint == 'refresh_token':
            token = base_query.filter_by(refresh_token=token).first()
        else:  # without token_type_hint
            token = base_query.filter_by(access_token=token).first()
            if not token:
                token = base_query.filter_by(refresh_token=token).first()
            return token

    def introspect_token(self, token):
        return {
            'active': True,
            'client_id': token.client.client_id,
            'token_type': token.token_type,
            'username': token.user.name,
            'metabrainz_user_id': token.user_id,
            'scope': token.get_scope(),
            'sub': token.user.name,
            'aud': token.client.client_id,
            'iss': 'https://metabrainz.com/',
            'exp': token.expires_at,
            'iat': token.issued_at,
        }

    def check_permission(self, token, client, request):
        # TODO: discuss restricting
        return True
