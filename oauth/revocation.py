from authlib.oauth2.rfc7009 import RevocationEndpoint

from oauth.model import db, OAuth2AccessToken, OAuth2RefreshToken


class OAuth2RevocationEndpoint(RevocationEndpoint):

    CLIENT_AUTH_METHODS = ["client_secret_post"]

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

    def revoke_token(self, token, request):
        if isinstance(token, OAuth2RefreshToken):
            # if the token is a refresh_token, revoke all associated access_tokens as well
            # in accordance with rfc 7009
            access_tokens = db.session.query(OAuth2AccessToken).filter_by(
                client_id=token.client_id,
                user_id=token.user_id,
                revoked=False
            ).all()
            for access_token in access_tokens:
                access_token.revoked = True
            db.session.add_all(access_tokens)

        token.revoked = True
        db.session.add(token)
        db.session.commit()
