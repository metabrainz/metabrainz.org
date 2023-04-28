from enum import Enum

from sqlalchemy.dialects.postgresql import ENUM

from metabrainz.model import db
from metabrainz.admin import AdminModelView


class DatasetUser(db.Model):
    """ This model defines what MetaBrainz datasets various users use. """
    __tablename__ = 'dataset_user'

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("dataset.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
