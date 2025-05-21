from typing import Type, Optional

from metabrainz.model import db


class UserPreference(db.Model):
    """ This model defines the digest preferences of Users."""
    __tablename__ = 'user_preference'

    id = db.Column(db.Integer, primary_key=True)
    musicbrainz_row_id = db.Column(db.Integer, unique=True)
    user_email = db.Column(db.Text, unique=True)
    digest = db.Column(db.Boolean, default=False)
    digest_age = db.Column(db.SmallInteger)
    
    # Todo: add foreign keys and relationship to user table.

    @classmethod
    def get(cls: Type["UserPreference"], **kwargs) -> Optional["UserPreference"]:
        return cls.query.filter_by(**kwargs).first()
    
    @classmethod
    def set_digest_info(cls: Type["UserPreference"], musicbrainz_row_id:int, digest:bool, digest_age:int) -> int:
        result = cls.query.filter(cls.musicbrainz_row_id == musicbrainz_row_id).update(
            {cls.digest:digest, cls.digest_age: digest_age}
        )
        db.session.commit()

        return result
