from metabrainz.model import db


class ReplicationControl(db.Model):
    __tablename__ = "replication_control"

    id = db.Column(db.Integer, primary_key=True)
    current_schema_sequence = db.Column(db.Integer, nullable=False)
    current_replication_sequence = db.Column(db.Integer)
    last_replication_date = db.Column(db.DateTime, nullable=False)
