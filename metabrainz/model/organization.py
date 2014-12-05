from metabrainz.model import db


class Organization(db.Model):
    __tablename__ = 'organization'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.Unicode, nullable=False)
    logo_url = db.Column(db.Unicode)
    website_url = db.Column(db.Unicode)
    api_url = db.Column(db.Unicode)
    description = db.Column(db.Unicode)  # How organization uses MetaBrainz projects

    contact_name = db.Column(db.Unicode, nullable=False)
    email = db.Column(db.Unicode, nullable=False)

    # Address
    address_street = db.Column(db.Unicode)
    address_city = db.Column(db.Unicode)
    address_state = db.Column(db.Unicode)
    address_postcode = db.Column(db.Unicode)
    address_country = db.Column(db.Unicode)

    tier_id = db.Column(db.Integer, db.ForeignKey('tier.id'))

    donations = db.relationship('Donation', backref='organization')
