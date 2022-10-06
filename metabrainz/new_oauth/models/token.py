import time

from authlib.integrations.sqla_oauth2 import OAuth2TokenMixin

from metabrainz.new_oauth.models import db
from metabrainz.new_oauth.models.user import OAuth2User


class OAuth2Token(db.Model, OAuth2TokenMixin):
    __tablename__ = 'token'
    __table_args__ = {
        'schema': 'oauth'
    }

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('oauth.user.id', ondelete='CASCADE'))
    user = db.relationship(OAuth2User)

    def is_refresh_token_active(self):
        if self.revoked:
            return False
        expires_at = self.issued_at + self.expires_in * 2
        return expires_at >= time.time()
