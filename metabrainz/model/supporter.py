from metabrainz.model import db


class Supporter(db.Model):
    __tablename__ = 'supporter'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.Unicode, nullable=False)
    last_name = db.Column(db.Unicode, nullable=False)
    email = db.Column(db.Unicode, nullable=False)
    anonymous = db.Column(db.Boolean, nullable=False)  # Show on site or not

    # Address
    address_street = db.Column(db.Unicode)
    address_city = db.Column(db.Unicode)
    address_state = db.Column(db.Unicode)
    address_postcode = db.Column(db.Unicode)
    address_country = db.Column(db.Unicode)
