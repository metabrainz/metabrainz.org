from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# All models must be imported there:
from .donation import Donation
