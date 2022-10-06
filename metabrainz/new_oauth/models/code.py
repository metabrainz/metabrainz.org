from authlib.oauth2.rfc6749 import AuthorizationCodeMixin
from sqlalchemy import Column, Integer, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import Identity

from metabrainz.new_oauth.models import Base
from metabrainz.new_oauth.models.client import OAuth2Client
from metabrainz.new_oauth.models.relation_scope import OAuth2CodeScope
from metabrainz.new_oauth.models.user import OAuth2User


class OAuth2AuthorizationCode(Base, AuthorizationCodeMixin):

    __tablename__ = "code"
    __table_args__ = {
        "schema": "oauth"
    }

    id = Column(Integer, Identity(), primary_key=True)
    user_id = Column(Integer, ForeignKey("oauth.user.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(Integer, ForeignKey("oauth.client.id", ondelete="CASCADE"), nullable=False)
    code = Column(Text, nullable=False, unique=True)
    redirect_uri = Column(Text, nullable=False)
    response_type = Column(Text, nullable=False)
    code_challenge = Column(Text)
    code_challenge_method = Column(Text)
    granted_at = Column(DateTime(timezone=True))

    user = relationship(OAuth2User)
    client = relationship(OAuth2Client)
    scopes = relationship("OAuth2Scope", secondary=OAuth2CodeScope)

    def get_redirect_uri(self):
        pass

    def get_scope(self):
        pass

