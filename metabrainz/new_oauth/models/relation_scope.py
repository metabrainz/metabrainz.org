from sqlalchemy import Integer
from sqlalchemy.sql.schema import Identity, Column, ForeignKey

from metabrainz.new_oauth.models import Base


class OAuth2TokenScope(Base):
    __tablename__ = "l_token_scope"
    __table_args__ = {
        "schema": "oauth"
    }
    id = Column(Integer, Identity(), primary_key=True)
    token_id = Column(Integer, ForeignKey("oauth.token.id", ondelete="CASCADE"), nullable=False)
    scope_id = Column(Integer, ForeignKey("oauth.scope.id", ondelete="CASCADE"), nullable=False)


class OAuth2CodeScope(Base):
    __tablename__ = "l_code_scope"
    __table_args__ = {
        "schema": "oauth"
    }
    id = Column(Integer, Identity(), primary_key=True)
    code_id = Column(Integer, ForeignKey("oauth.code.id", ondelete="CASCADE"), nullable=False)
    scope_id = Column(Integer, ForeignKey("oauth.scope.id", ondelete="CASCADE"), nullable=False)
