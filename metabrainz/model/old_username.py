from sqlalchemy import Column, Integer, Identity, Text, DateTime, Index, func

from metabrainz.model import db


class OldUsername(db.Model):
    __tablename__ = 'old_username'

    id = Column(Integer, Identity(), primary_key=True)
    username = Column(Text, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    __table_args__ = (
        Index("old_username_username_idx", func.lower(username)),
    )

    @classmethod
    def get(cls, username):
        return cls.query.filter(func.lower(cls.username) == func.lower(username)).first()
