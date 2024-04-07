from sqlalchemy import Column, Integer, String, Boolean

from oauth.model import db


class User(db.Model):

    # TODO: Use a read only connection to MB DB
    __bind_key__ = "musicbrainz"
    __tablename__ = "editor"
    __table_args__ = {"schema": "musicbrainz"}

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    deleted = Column(Boolean, nullable=False)
