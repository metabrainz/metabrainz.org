from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# All models must be imported there:
from .user import User
from .token import Token
from .token_log import TokenLog
from .access_log import AccessLog
from .tier import Tier
from .payment import Payment
