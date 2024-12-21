from flask_login import UserMixin
from sqlalchemy import Column, Integer, Identity, Text, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.orm.attributes import Mapped

from metabrainz.model import db


class User(db.Model, UserMixin):
    __tablename__ = "user"

    id = Column(Integer, Identity(), primary_key=True)
    name = Column(Text, nullable=False)  # TODO: add a uniqueness constraint maybe in conjunction with the deleted field
    password = Column(Text, nullable=False)  # TODO: add a constraint to ensure password is cleared when deleted field is set

    email = Column(Text, unique=True) # TODO: check if unique should be only deleted = false
    unconfirmed_email = Column(Text)
    email_confirmed_at = Column(DateTime(timezone=True))

    member_since = Column(DateTime(timezone=True), default=func.now())
    last_login_at = Column(DateTime(timezone=True), default=func.now())
    last_updated = Column(DateTime(timezone=True), default=func.now())

    deleted = Column(Boolean, default=False)

    supporter: Mapped["Supporter"] = relationship("Supporter", uselist=False, back_populates="user", lazy="joined")

    def get_user_id(self):
        return self.id

    def get_email_any(self):
        return self.email or self.unconfirmed_email

    def is_email_confirmed(self):
        return self.email is not None

    @classmethod
    def add(cls, **kwargs):
        from metabrainz import bcrypt

        password = kwargs.pop("password")
        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        new_user = cls(name=kwargs.pop("name"), password=password_hash, unconfirmed_email=kwargs.pop("unconfirmed_email"))
        if kwargs:
            raise TypeError("Unexpected **kwargs: %r" % (kwargs,))
        db.session.add(new_user)
        return new_user

    @classmethod
    def get(cls, **kwargs):
        row = cls.query.filter_by(**kwargs).first()
        if row:
            return row

        if "email" in kwargs:
            kwargs["unconfirmed_email"] = kwargs.pop("email")
            return cls.query.filter_by(**kwargs).first()

        return None
