from metabrainz.model import db


class Tier(db.Model):
    """This model defines tier of support that people can sign up to."""
    __tablename__ = 'tier'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode, nullable=False)
    short_desc = db.Column(db.Unicode)
    long_desc = db.Column(db.Unicode)
    price = db.Column(db.Numeric(11, 2), nullable=False)  # per month

    # Primary tiers are shown on the signup page. Secondary plans (along with
    # repeating primary plans) are listed on the "view all tiers" page that
    # lists everything.
    primary = db.Column(db.Boolean, nullable=False, default=False)
