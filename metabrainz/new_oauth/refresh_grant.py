from authlib.oauth2.rfc6749 import grants

from metabrainz.new_oauth.models import db
from metabrainz.new_oauth.models.token import OAuth2Token
from metabrainz.new_oauth.models.user import OAuth2User


class RefreshTokenGrant(grants.RefreshTokenGrant):

    def authenticate_refresh_token(self, refresh_token):
        token = OAuth2Token.query.filter_by(refresh_token=refresh_token).first()
        if token and token.is_refresh_token_active():
            return token

    def authenticate_user(self, credential):
        return OAuth2User.query.get(credential.user_id)

    def revoke_old_credential(self, credential):
        credential.revoked = True
        db.session.add(credential)
        db.session.commit()
