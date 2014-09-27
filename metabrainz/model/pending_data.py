from metabrainz.model import db


class PendingData(db.Model):
    __tablename__ = "PendingData"

    seq_id = db.Column("SeqId", db.Integer, primary_key=True)
    is_key = db.Column("IsKey", db.Boolean, nullable=False)
    data = db.Column("Data", db.String)
