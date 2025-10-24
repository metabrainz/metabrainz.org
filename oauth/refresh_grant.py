from authlib.oauth2.rfc6749 import grants, InvalidRequestError

from metabrainz.model.user import User
from oauth.model import db, OAuth2RefreshToken, OAuth2AccessToken


class RefreshTokenGrant(grants.RefreshTokenGrant):

    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_basic", "client_secret_post"]
    INCLUDE_NEW_REFRESH_TOKEN = True

    def authenticate_refresh_token(self, refresh_token):
        token = db.session\
            .query(OAuth2RefreshToken)\
            .filter_by(refresh_token=refresh_token)\
            .first()
        # revoked token used, revoke other tokens for same client and user
        # https://datatracker.ietf.org/doc/html/rfc6819#section-5.2.2.3
        if token and token.revoked:
            db.session.query(OAuth2AccessToken).filter_by(
                client_id=token.client_id,
                user_id=token.user_id
            ).update({OAuth2AccessToken.revoked: True})
            db.session.query(OAuth2RefreshToken).filter_by(
                client_id=token.client_id,
                user_id=token.user_id
            ).update({OAuth2RefreshToken.revoked: True})
            db.session.commit()
            raise InvalidRequestError("\"refresh_token\" in request was already revoked.")
        return token

    def authenticate_user(self, credential):
        return User.get(id=credential.user_id)

    def revoke_old_credential(self, credential):
        old_access_tokens = db.session\
            .query(OAuth2AccessToken)\
            .filter_by(user_id=credential.user_id, client_id=credential.client_id, revoked=False)\
            .order_by(OAuth2AccessToken.issued_at)\
            .all()

        if len(old_access_tokens) > 0:
            old_access_tokens.pop()  # do not revoke the latest issued token
            for token in old_access_tokens:
                token.revoked = True

        credential.revoked = True
        db.session.commit()
