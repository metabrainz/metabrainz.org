from sqlalchemy import Column, Integer, Identity, Text, DateTime, func

from metabrainz.model import db


class OldUsername(db.Model):
    __tablename__ = 'old_username'

    id = Column(Integer, Identity(), primary_key=True)
    username = Column(Text, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
