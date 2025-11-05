from typing import Type, Optional

from metabrainz.model import db

DEFAULT_DIGEST_AGE = 7 # in days.

class UserPreference(db.Model):
    """ This model defines the digest preferences of Users."""
    __tablename__ = 'user_preference'

    id = db.Column(db.Integer, primary_key=True)
    musicbrainz_row_id = db.Column(db.Integer, unique=True)
    user_email = db.Column(db.Text, unique=True)
    notifications_enabled = db.Column(db.Boolean, default=True)
    digest = db.Column(db.Boolean, default=False)
    digest_age = db.Column(db.SmallInteger, default=DEFAULT_DIGEST_AGE)
    
    # Todo: add foreign keys and relationship to user table.

    @classmethod
    def get(cls: Type["UserPreference"], **kwargs) -> Optional["UserPreference"]:
        return cls.query.filter_by(**kwargs).first()
    
    @classmethod
    def set_notification_preference(
        cls: Type["UserPreference"],
        musicbrainz_row_id: int,
        notifications_enabled: bool,
        digest: bool,
        digest_age: Optional[int] = None,
    ) -> Optional["UserPreference"]:
        params = {
            cls.notifications_enabled: notifications_enabled,
            cls.digest: digest,
            cls.digest_age: digest_age,
        }

        cls.query.filter(cls.musicbrainz_row_id == musicbrainz_row_id).update(params)
        db.session.commit()
        
        result = cls.query.filter_by(musicbrainz_row_id = musicbrainz_row_id).first()
        return result
