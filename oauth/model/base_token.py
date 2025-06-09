from datetime import timedelta, datetime, timezone

from authlib.integrations.flask_oauth2.requests import FlaskOAuth2Request
from authlib.oauth2.rfc6749 import TokenMixin
from sqlalchemy import func, Column, Integer, DateTime, ForeignKey, Boolean, Identity
from sqlalchemy.orm import relationship, declared_attr

from oauth.model import db
from oauth.model.client import OAuth2Client
from oauth.model.code import OAuth2AuthorizationCode
from oauth.model.scope import get_scopes


class OAuth2BaseToken(TokenMixin):
    __table_args__ = {
        "schema": "oauth"
    }

    id = Column(Integer, Identity(), primary_key=True)
    issued_at = Column(DateTime(timezone=True), default=func.now())
    expires_in = Column(Integer)
    revoked = Column(Boolean, default=False)

    @declared_attr
    def client_id(self):
        return Column(Integer, ForeignKey("oauth.client.id", ondelete="CASCADE"), nullable=False)

    @declared_attr
    def client(self):
        return relationship(OAuth2Client)

    @declared_attr
    def authorization_code_id(self):
        return Column(Integer, ForeignKey("oauth.code.id"))

    @declared_attr
    def authorization_code(self):
        return relationship(OAuth2AuthorizationCode)

    def get_client_id(self):
        return self.client.client_id

    def get_expires_in(self):
        return self.expires_in

    def get_expires_at(self):
        return self.issued_at + timedelta(seconds=self.expires_in)

    def check_client(self, client):
        return self.client_id == client.id

    def is_expired(self):
        return datetime.now(tz=timezone.utc) >= self.get_expires_at()

    def is_revoked(self):
        return self.revoked


def save_token(token_data, request: FlaskOAuth2Request):
    from oauth.model.access_token import OAuth2AccessToken
    from oauth.model.refresh_token import OAuth2RefreshToken

    refresh_token = None
    access_token_scopes = []
    refresh_token_scopes = []
    authorization_code_id = None

    # saving token for authorization code grant
    if request.data.get("grant_type") == "authorization_code":
        authorization_code = db.session\
            .query(OAuth2AuthorizationCode)\
            .filter_by(code=request.data.get("code"))\
            .first()
        authorization_code_id = authorization_code.id
        refresh_token = token_data["refresh_token"]
        access_token_scopes = authorization_code.scopes
        refresh_token_scopes = authorization_code.scopes
    elif request.data.get("response_type") == "token":  # saving token for implicit grant
        access_token_scopes = get_scopes(db.session, request.data.get("scope"))
    elif request.data.get("grant_type") == "refresh_token":
        # if only a subset of scopes is requested, use that for access token but retain
        # the original scopes for the refresh token
        if request.data.get("scope"):
            access_token_scopes = get_scopes(db.session, request.data.get("scope"))
        else:
            access_token_scopes = request.refresh_token.scopes

        refresh_token = token_data.get("refresh_token") or request.refresh_token.refresh_token
        refresh_token_scopes = request.refresh_token.scopes
    elif request.data.get("grant_type") == "client_credentials":
        access_token_scopes = get_scopes(db.session, request.data.get("scope"))

    if request.data.get("grant_type") == "client_credentials":
        user_id = None
    else:
        user_id = request.user.id

    access_token = OAuth2AccessToken(
        client_id=request.client.id,
        user_id=user_id,
        access_token=token_data["access_token"],
        expires_in=token_data["expires_in"],
        scopes=access_token_scopes,
        authorization_code_id=authorization_code_id
    )
    db.session.add(access_token)

    if refresh_token is not None:
        refresh_token = OAuth2RefreshToken(
            client_id=request.client.id,
            user_id=user_id,
            refresh_token=refresh_token,
            expires_in=token_data["expires_in"],  # TODO: fix refresh token expiry, for existing retain or reset ?
            scopes=refresh_token_scopes,
            authorization_code_id=authorization_code_id
        )
        db.session.add(refresh_token)

    db.session.commit()
