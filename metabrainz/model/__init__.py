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
from .user_preference import UserPreference