from sqlalchemy import Column, DateTime, ForeignKey, Identity, Integer, func
from sqlalchemy.orm import relationship

from metabrainz.model import db
from metabrainz.model.oauth.client import OAuth2Client


class OAuth2ProvisionedUser(db.Model):
    """An account an OAuth client created through a registration request.

    Records who an account came from.
    """
    __tablename__ = "provisioned_user"
    __table_args__ = {"schema": "oauth"}

    id = Column(Integer, Identity(), primary_key=True)
    # an account is provisioned once, by the one client that created it
    user_id = Column(Integer, nullable=False, unique=True)
    client_id = Column(Integer, ForeignKey("oauth.client.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    client = relationship(OAuth2Client)
