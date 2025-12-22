from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# All models must be imported there:
from .supporter import Supporter
from .token import Token
from .token_log import TokenLog
from .access_log import AccessLog
from .tier import Tier
from .payment import Payment
from .dataset import Dataset
from .dataset_supporter import DatasetSupporter

from .oauth.client import OAuth2Client
from .oauth.relation_scope import OAuth2AccessTokenScope, OAuth2RefreshTokenScope, OAuth2CodeScope
from .oauth.scope import OAuth2Scope, get_scopes
from .oauth.code import OAuth2AuthorizationCode
from .oauth.access_token import OAuth2AccessToken
from .oauth.refresh_token import OAuth2RefreshToken
from .oauth.base_token import save_token

from .webhook_delivery import WebhookDelivery
from .webhook import Webhook
from .domain_blacklist import DomainBlacklist
