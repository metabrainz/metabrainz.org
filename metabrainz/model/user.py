from flask_login import UserMixin
from sqlalchemy import Column, Integer, Identity, Text, DateTime, func, Boolean

from metabrainz.model import db


class User(db.Model, UserMixin):
    __tablename__ = "user"

    id = Column(Integer, Identity(), primary_key=True)
    name = Column(Text, nullable=False)  # TODO: add a uniqueness constraint maybe in conjunction with the deleted field
    password = Column(Text, nullable=False)  # TODO: add a constraint to ensure password is cleared when deleted field is set

    email = Column(Text)
    unconfirmed_email = Column(Text)

    member_since = Column(DateTime(timezone=True), default=func.now())
    last_login_at = Column(DateTime(timezone=True), default=func.now())
    last_updated = Column(DateTime(timezone=True), default=func.now())

    deleted = Column(Boolean, default=False)

    def get_user_id(self):
        return self.id

    def is_email_confirmed(self):
        return self.email_confirmed_at is not None

    @classmethod
    def add(cls, **kwargs):
        new_user = cls(
            name=kwargs.pop('name'),
            password=kwargs.pop('password_hash'),
            email=kwargs.pop('email')
        )
        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)
        db.session.add(new_user)
        db.session.commit()
        return new_user

    @classmethod
    def get(cls, **kwargs):
        return cls.query.filter_by(**kwargs).first()
