from metabrainz.model import db


class Donation(db.Model):
    __tablename__ = "donation"

    id = db.Column(db.Integer, primary_key=True)

    # Personal details
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    moderator = db.Column(db.String, server_default="")
    contact = db.Column(db.Boolean, server_default="FALSE")
    anonymous = db.Column("anon", db.Boolean, server_default="FALSE")
    address_street = db.Column(db.String, server_default="")
    address_city = db.Column(db.String, server_default="")
    address_state = db.Column(db.String, server_default="")
    address_postcode = db.Column(db.String, server_default="")
    address_country = db.Column(db.String, server_default="")

    # Transaction details
    timestamp = db.Column(db.DateTime, server_default="now()")
    paypal_trans_id = db.Column(db.String(32), nullable=False)
    amount = db.Column(db.Numeric(11, 2), nullable=False)
    fee = db.Column(db.String, server_default="")
    memo = db.Column(db.String, server_default="")
