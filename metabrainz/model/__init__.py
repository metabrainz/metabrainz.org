from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# All models must be imported there:
from .organization import Organization
from .donation import Donation
from .tier import Tier
