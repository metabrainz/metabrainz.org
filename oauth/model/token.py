from datetime import timedelta, datetime, timezone

from authlib.integrations.flask_oauth2.requests import FlaskOAuth2Request
from authlib.oauth2.rfc6749 import TokenMixin
from authlib.oauth2.rfc6749.util import scope_to_list
from sqlalchemy import func, Column, Integer, DateTime, Text, ForeignKey, Boolean, Identity
from sqlalchemy.orm import relationship

from oauth.model import db
from oauth.model.client import OAuth2Client
from oauth.model.code import OAuth2AuthorizationCode
from oauth.model.relation_scope import OAuth2TokenScope
from oauth.model.scope import OAuth2Scope, get_scopes


class OAuth2Token(db.Model, TokenMixin):
    __tablename__ = "token"
    __table_args__ = {
        "schema": "oauth"
    }

    id = Column(Integer, Identity(), primary_key=True)
    # no FK to user table because user data lives in MB db
    user_id = Column(Integer, nullable=False)
    client_id = Column(Integer, ForeignKey("oauth.client.id", ondelete="CASCADE"), nullable=False)
    access_token = Column(Text, nullable=False, unique=True)
    refresh_token = Column(Text, index=True)  # nullable, because not all grants have refresh token
    issued_at = Column(DateTime(timezone=True), default=func.now())
    expires_in = Column(Integer)
    revoked = Column(Boolean, default=False)

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


def save_token(token_data, request: FlaskOAuth2Request):
    # saving token for authorization code grant
    if request.data.get("grant_type") == "authorization_code":
        _code = db.session.query(OAuth2AuthorizationCode).filter_by(code=request.data.get("code")).first()
        scopes = _code.scopes
        refresh_token = token_data["refresh_token"]
    elif request.data.get("response_type") == "token":  # saving token for implicit grant
        scopes = get_scopes(db.session, request.data.get("scope"))
        refresh_token = None
    elif request.data.get("grant_type") == "refresh_token":
        scopes = request.refresh_token.scopes
        refresh_token = token_data.get("refresh_token") or request.refresh_token.refresh_token

    token = OAuth2Token(
        client_id=request.client.id,
        user_id=request.user.id,
        access_token=token_data["access_token"],
        refresh_token=refresh_token,
        expires_in=token_data["expires_in"],
        scopes=scopes
    )
    db.session.add(token)
    db.session.commit()
