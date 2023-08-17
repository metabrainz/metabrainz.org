from sqlalchemy import Column, Integer, Identity, Text, DateTime, func, Date, Boolean

from metabrainz.new_oauth.models import Base


class OAuth2User(Base):
    __tablename__ = "user"
    __table_args__ = {
        "schema": "oauth"
    }

    id = Column(Integer, Identity(), primary_key=True)
    name = Column(Text, nullable=False)
    email = Column(Text)
    unconfirmed_email = Column(Text)
    website = Column(Text)
    member_since = Column(DateTime(timezone=True), default=func.now())
    email_confirm_date = Column(DateTime(timezone=True))
    last_login_date = Column(DateTime(timezone=True), default=func.now())
    last_updated = Column(DateTime(timezone=True), default=func.now())
    birth_date = Column(Date)
    gender = Column(Integer)  # TODO: add FK to gender.id
    password = Column(Text, nullable=False)
    ha1 = Column(Text, nullable=False)
    deleted = Column(Boolean, default=False)
