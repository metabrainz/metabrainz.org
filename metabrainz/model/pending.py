from metabrainz.model import db


class Pending(db.Model):
    __tablename__ = "Pending"

    seq_id = db.Column("SeqId", db.Integer, primary_key=True)
    table_name = db.Column("TableName", db.String, nullable=False)
    op = db.Column("Op", db.String(1))
    xid = db.Column("XID", db.Integer, nullable=False)
