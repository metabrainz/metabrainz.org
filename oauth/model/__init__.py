from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .client import OAuth2Client
from .relation_scope import OAuth2TokenScope, OAuth2CodeScope
from .scope import OAuth2Scope
from .token import OAuth2Token
from .code import OAuth2AuthorizationCode
