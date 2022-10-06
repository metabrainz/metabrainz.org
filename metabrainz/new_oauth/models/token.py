from datetime import timedelta

from authlib.oauth2.rfc6749 import TokenMixin
from authlib.oauth2.rfc6749.util import scope_to_list
from sqlalchemy import func, Column, Integer, DateTime, Text, ForeignKey, Boolean, Identity
from sqlalchemy.orm import relationship

from metabrainz.new_oauth.models import Base
from metabrainz.new_oauth.models.client import OAuth2Client
from metabrainz.new_oauth.models.relation_scope import OAuth2TokenScope
from metabrainz.new_oauth.models.user import OAuth2User


class OAuth2Token(Base, TokenMixin):
    __tablename__ = "token"
    __table_args__ = {
        "schema": "oauth"
    }

    id = Column(Integer, Identity(), primary_key=True)
    user_id = Column(Integer, ForeignKey("oauth.user.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(Integer, ForeignKey("oauth.client.id", ondelete="CASCADE"), nullable=False)
    access_token = Column(Text, nullable=False, unique=True)
    refresh_token = Column(Text, index=True)  # nullable, because not all grants have refresh token
    issued_at = Column(DateTime(timezone=True), default=func.now())
    expires_in = Column(Integer)
    revoked = Column(Boolean, default=False)

    user = relationship(OAuth2User)
    client = relationship(OAuth2Client)
    scopes = relationship("OAuth2Scope", secondary=OAuth2TokenScope)

    def get_client_id(self):
        return self.client_id

    def get_scope(self):
        return scope_to_list([s.name for s in self.scopes])

    def get_expires_in(self):
        return self.expires_in

    def get_expires_at(self):
        return self.issued_at + timedelta(seconds=self.expires_in)

    def is_refresh_token_active(self):
        return self.revoked
