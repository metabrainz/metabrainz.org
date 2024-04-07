from authlib.oauth2.rfc6749 import grants

from oauth.model import db
from oauth.model.token import OAuth2Token
from oauth.model.user import User


class RefreshTokenGrant(grants.RefreshTokenGrant):

    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_post"]
    INCLUDE_NEW_REFRESH_TOKEN = True

    def authenticate_refresh_token(self, refresh_token):
        token = db.session\
            .query(OAuth2Token)\
            .filter_by(refresh_token=refresh_token)\
            .first()
        if token and token.is_refresh_token_active():
            return token

    def authenticate_user(self, credential):
        return db.session\
            .query(User)\
            .filter_by(id=credential.user_id)\
            .first()

    def revoke_old_credential(self, credential):
        credential.revoked = True
        db.session.add(credential)
        db.session.commit()
