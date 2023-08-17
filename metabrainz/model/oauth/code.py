from authlib.oauth2.rfc6749 import AuthorizationCodeMixin
from authlib.oauth2.rfc6749.util import scope_to_list
from sqlalchemy import Column, Integer, ForeignKey, Text, DateTime, func
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import Identity

from metabrainz.model import db
from metabrainz.model.oauth.client import OAuth2Client
from metabrainz.model.oauth.relation_scope import OAuth2CodeScope
from metabrainz.model.oauth.scope import OAuth2Scope
from metabrainz.model.user import User


class OAuth2AuthorizationCode(db.Model, AuthorizationCodeMixin):

    __tablename__ = "code"
    __table_args__ = {
        "schema": "oauth"
    }

    id = Column(Integer, Identity(), primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(Integer, ForeignKey("oauth.client.id", ondelete="CASCADE"), nullable=False)
    code = Column(Text, nullable=False, unique=True)
    redirect_uri = Column(Text, nullable=False)
    response_type = Column(Text, nullable=False)
    code_challenge = Column(Text)
    code_challenge_method = Column(Text)
    granted_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    user = relationship(User)
    client = relationship(OAuth2Client)
    scopes = relationship(OAuth2Scope, secondary=OAuth2CodeScope)

    def get_redirect_uri(self):
        return self.redirect_uri

    def get_scope(self):
        return scope_to_list([s.name for s in self.scopes])
