from authlib.oauth2.rfc6749 import grants

from metabrainz.new_oauth.models import db
from metabrainz.new_oauth.models.token import OAuth2Token
from metabrainz.new_oauth.models.user import OAuth2User


class RefreshTokenGrant(grants.RefreshTokenGrant):

    def authenticate_refresh_token(self, refresh_token):
        token = db.session\
            .query(OAuth2Token)\
            .filter_by(refresh_token=refresh_token)\
            .first()
        if token and token.is_refresh_token_active():
            return token

    def authenticate_user(self, credential):
        # TODO: fix impl
        # return db.session\
        #     .query(OAuth2User)\
        #     .filter_by(user_id=credential.user_id)\
        #     .first()
        pass

    def revoke_old_credential(self, credential):
        credential.revoked = True
        db.session.add(credential)
        db.session.commit()
