from sqlalchemy import Integer
from sqlalchemy.sql.schema import Identity, Column, ForeignKey

from metabrainz.model import db


# the restricted scopes a client is allowed to request, see OAuth2Scope.restricted
OAuth2ClientScope = db.Table(
    "l_client_scope",
    Column("id", Integer, Identity(), primary_key=True),
    Column("client_id", Integer, ForeignKey("oauth.client.id", ondelete="CASCADE"), nullable=False),
    Column("scope_id", Integer, ForeignKey("oauth.scope.id", ondelete="CASCADE"), nullable=False),
    schema="oauth"
)

OAuth2AccessTokenScope = db.Table(
    "l_access_token_scope",
    Column("id", Integer, Identity(), primary_key=True),
    Column("access_token_id", Integer, ForeignKey("oauth.access_token.id", ondelete="CASCADE"), nullable=False),
    Column("scope_id", Integer, ForeignKey("oauth.scope.id", ondelete="CASCADE"), nullable=False),
    schema="oauth"
)

OAuth2RefreshTokenScope = db.Table(
    "l_refresh_token_scope",
    Column("id", Integer, Identity(), primary_key=True),
    Column("refresh_token_id", Integer, ForeignKey("oauth.refresh_token.id", ondelete="CASCADE"), nullable=False),
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
