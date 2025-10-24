from flask_sqlalchemy import SQLAlchemy

from metabrainz.model import db

from .client import OAuth2Client
from .relation_scope import OAuth2AccessTokenScope, OAuth2RefreshTokenScope, OAuth2CodeScope
from .scope import OAuth2Scope
from .code import OAuth2AuthorizationCode
from .access_token import OAuth2AccessToken
from .refresh_token import OAuth2RefreshToken
