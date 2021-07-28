from metabrainz.new_oauth.models import db
from authlib.integrations.sqla_oauth2 import OAuth2ClientMixin


class OAuth2Client(db.Model, OAuth2ClientMixin):
    __tablename__ = 'oauth2_client'

    id = db.Column(db.Integer, primary_key=True)

    # we probably want to do the migration in stages, so if the users are migrated
    # at a different time than clients, we can temporarily drop the FK.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    user = db.relationship('User')
