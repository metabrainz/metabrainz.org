from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .client import OAuth2Client
from .relation_scope import OAuth2AccessTokenScope, OAuth2RefreshTokenScope, OAuth2CodeScope
from .scope import OAuth2Scope
from .access_token import OAuth2AccessToken
from .refresh_token import OAuth2RefreshToken
from .code import OAuth2AuthorizationCode
