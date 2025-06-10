from authlib.oauth2.rfc6749.util import scope_to_list
from sqlalchemy import Column, Text, Integer
from sqlalchemy.orm import relationship

from oauth.model import db
from oauth.model.base_token import OAuth2BaseToken
from oauth.model.relation_scope import OAuth2RefreshTokenScope
from oauth.model.scope import OAuth2Scope


class OAuth2RefreshToken(db.Model, OAuth2BaseToken):
    __tablename__ = "refresh_token"

    user_id = Column(Integer, nullable=False)
    refresh_token = Column(Text, nullable=False, unique=True)
    scopes = relationship(OAuth2Scope, secondary=OAuth2RefreshTokenScope)

    def get_scope(self):
        return scope_to_list([s.name for s in self.scopes])
