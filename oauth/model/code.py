from datetime import timedelta, datetime, timezone

from authlib.oauth2.rfc6749 import AuthorizationCodeMixin
from authlib.oauth2.rfc6749.util import scope_to_list
from sqlalchemy import Column, Integer, ForeignKey, Text, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import Identity

from oauth.model import db
from oauth.model.client import OAuth2Client
from oauth.model.relation_scope import OAuth2CodeScope
from oauth.model.scope import OAuth2Scope


class OAuth2AuthorizationCode(db.Model, AuthorizationCodeMixin):

    __tablename__ = "code"
    __table_args__ = {
        "schema": "oauth"
    }

    id = Column(Integer, Identity(), primary_key=True)
    # no FK to user table because user data lives in MB db
    user_id = Column(Integer, nullable=False)
    client_id = Column(Integer, ForeignKey("oauth.client.id", ondelete="CASCADE"), nullable=False)
    code = Column(Text, nullable=False, unique=True)
    redirect_uri = Column(Text, nullable=False)
    code_challenge = Column(Text)
    code_challenge_method = Column(Text)
    issued_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    expires_in = Column(Integer)
    revoked = Column(Boolean, default=False)

    client = relationship(OAuth2Client)
    scopes = relationship(OAuth2Scope, secondary=OAuth2CodeScope)

    def get_redirect_uri(self):
        return self.redirect_uri

    def get_scope(self):
        return scope_to_list([s.name for s in self.scopes])

    def is_expired(self):
        expires_at = self.issued_at + timedelta(seconds=self.expires_in)
        return datetime.now(tz=timezone.utc) >= expires_at
