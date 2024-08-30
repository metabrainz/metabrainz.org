from metabrainz.model import db


class DatasetSupporter(db.Model):
    """ This model defines what MetaBrainz datasets various supporters use. """
    __tablename__ = 'dataset_supporter'

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("dataset.id"))
    supporter_id = db.Column(db.Integer, db.ForeignKey("supporter.id"))
