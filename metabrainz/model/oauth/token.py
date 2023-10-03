from datetime import timedelta, datetime, timezone

from authlib.oauth2.rfc6749 import TokenMixin
from authlib.oauth2.rfc6749.util import scope_to_list
from sqlalchemy import func, Column, Integer, DateTime, Text, ForeignKey, Boolean, Identity
from sqlalchemy.orm import relationship

from metabrainz.model import db
from metabrainz.model.oauth.client import OAuth2Client
from metabrainz.model.oauth.code import OAuth2AuthorizationCode
from metabrainz.model.oauth.relation_scope import OAuth2TokenScope
from metabrainz.model.oauth.scope import OAuth2Scope, get_scopes
from metabrainz.model.user import User


class OAuth2Token(db.Model, TokenMixin):
    __tablename__ = "token"
    __table_args__ = {
        "schema": "oauth"
    }

    id = Column(Integer, Identity(), primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(Integer, ForeignKey("oauth.client.id", ondelete="CASCADE"), nullable=False)
    access_token = Column(Text, nullable=False, unique=True)
    refresh_token = Column(Text, index=True)  # nullable, because not all grants have refresh token
    issued_at = Column(DateTime(timezone=True), default=func.now())
    expires_in = Column(Integer)
    revoked = Column(Boolean, default=False)

    user = relationship(User)
    client = relationship(OAuth2Client)
    scopes = relationship(OAuth2Scope, secondary=OAuth2TokenScope)

    def get_client_id(self):
        return self.client.client_id

    def get_scope(self):
        return scope_to_list([s.name for s in self.scopes])

    def get_expires_in(self):
        return self.expires_in

    def get_expires_at(self):
        return self.issued_at + timedelta(seconds=self.expires_in)

    def is_refresh_token_active(self):
        return not self.revoked

    def check_client(self, client):
        return self.client_id == client.id

    def is_expired(self):
        return datetime.now(tz=timezone.utc) >= self.get_expires_at()

    def is_revoked(self):
        return self.revoked


def save_token(token_data, request):
    # TODO: Handle refresh token
    token = OAuth2Token(
        client_id=request.client.id,
        user_id=request.user.id,
        access_token=token_data["access_token"],
        expires_in=token_data["expires_in"],
        scopes=request.authorization_code.scopes
    )
    db.session.add(token)
    db.session.commit()
