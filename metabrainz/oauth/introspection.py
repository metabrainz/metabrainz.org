from authlib.oauth2.rfc7662 import IntrospectionEndpoint

from metabrainz.model.user import User

from metabrainz.model import db, OAuth2AccessToken, OAuth2RefreshToken


class OAuth2IntrospectionEndpoint(IntrospectionEndpoint):

    CLIENT_AUTH_METHODS = ["client_secret_basic", "client_secret_post"]

    def query_token(self, token_str, token_type_hint):
        if token_type_hint == "access_token":
            token = db.session.query(OAuth2AccessToken).filter_by(access_token=token_str).first()
        elif token_type_hint == "refresh_token":
            token = db.session.query(OAuth2RefreshToken).filter_by(refresh_token=token_str).first()
        else:  # without token_type_hint
            token = db.session.query(OAuth2AccessToken).filter_by(access_token=token_str).first()
            if not token:
                token = db.session.query(OAuth2RefreshToken).filter_by(refresh_token=token_str).first()
        return token

    def introspect_token(self, token):
        data = {
            "client_id": token.client.client_id,
            "token_type": "Bearer",
            "scope": token.get_scope(),
            "issued_by": "https://metabrainz.org/",
            "expires_at": int(token.get_expires_at().timestamp()),
            "issued_at": int(token.issued_at.timestamp()),
        }

        if token.user_id is not None:
            data["metabrainz_user_id"] = token.user_id
            user = User.get(id=token.user_id)
            sub = user.name
        else:
            # user_id is None for client credentials grant
            sub = token.client.name
        data["sub"] = sub

        return data

    def check_permission(self, token, client, request):
        # any client can introspect any token
        # todo: consider restricting to only *brainz clients having introspection rights
        return True
