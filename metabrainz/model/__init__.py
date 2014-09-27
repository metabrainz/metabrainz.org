from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# All models must be imported there:
from .donation import Donation
from .donation_historical import DonationHistorical
from .pending import Pending
from .pending_data import PendingData
from .replication_control import ReplicationControl
