from sqlalchemy import Integer
from sqlalchemy.sql.schema import Identity, Column, ForeignKey, Table

from metabrainz.new_oauth.models import Base


OAuth2TokenScope = Table(
    "l_token_scope",
    Base.metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("token_id", Integer, ForeignKey("oauth.token.id", ondelete="CASCADE"), nullable=False),
    Column("scope_id", Integer, ForeignKey("oauth.scope.id", ondelete="CASCADE"), nullable=False),
    schema="oauth"
)

OAuth2CodeScope = Table(
    "l_code_scope",
    Base.metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("code_id", Integer, ForeignKey("oauth.code.id", ondelete="CASCADE"), nullable=False),
    Column("scope_id", Integer, ForeignKey("oauth.scope.id", ondelete="CASCADE"), nullable=False),
    schema="oauth"
)
