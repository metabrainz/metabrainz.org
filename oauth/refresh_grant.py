from authlib.oauth2.rfc6749 import grants

from oauth import login
from oauth.model import db, OAuth2RefreshToken, OAuth2AccessToken


class RefreshTokenGrant(grants.RefreshTokenGrant):

    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_basic", "client_secret_post"]
    INCLUDE_NEW_REFRESH_TOKEN = True

    def authenticate_refresh_token(self, refresh_token):
        return db.session\
            .query(OAuth2RefreshToken)\
            .filter_by(refresh_token=refresh_token, revoked=False)\
            .first()

    def authenticate_user(self, credential):
        return login.load_user_from_db(credential.user_id)

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
