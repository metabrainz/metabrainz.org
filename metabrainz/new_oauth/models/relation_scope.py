from sqlalchemy import Integer
from sqlalchemy.sql.schema import Identity, Column, ForeignKey, Table

from metabrainz.model import db


OAuth2TokenScope = db.Table(
    "l_token_scope",
    Column("id", Integer, Identity(), primary_key=True),
    Column("token_id", Integer, ForeignKey("oauth.token.id", ondelete="CASCADE"), nullable=False),
    Column("scope_id", Integer, ForeignKey("oauth.scope.id", ondelete="CASCADE"), nullable=False),
    schema="oauth"
)

OAuth2CodeScope = db.Table(
    "l_code_scope",
    Column("id", Integer, Identity(), primary_key=True),
    Column("code_id", Integer, ForeignKey("oauth.code.id", ondelete="CASCADE"), nullable=False),
    Column("scope_id", Integer, ForeignKey("oauth.scope.id", ondelete="CASCADE"), nullable=False),
    schema="oauth"
)
