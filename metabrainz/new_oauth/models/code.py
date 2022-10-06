from authlib.integrations.sqla_oauth2 import OAuth2AuthorizationCodeMixin
from metabrainz.new_oauth.models import db


class OAuth2AuthorizationCode(db.Model, OAuth2AuthorizationCodeMixin):
    __tablename__ = 'code'
    __table_args__ = {
        'schema': 'oauth'
    }

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('oauth.user.id', ondelete='CASCADE'))
    user = db.relationship('OAuth2User')
