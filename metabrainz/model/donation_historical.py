from metabrainz.model import db


class DonationHistorical(db.Model):
    __tablename__ = "donation_historical"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(11, 2), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
