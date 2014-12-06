from metabrainz.model import db
from flask_admin.contrib.sqla import ModelView


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

    organizations = db.relationship('Organization', backref='tier')

    def __unicode__(self):
        return self.name

    @classmethod
    def get_all(cls):
        """Returns list of all tiers sorted by price."""
        return cls.query.order_by(cls.price).all()


class TierAdminView(ModelView):
    column_labels = dict(
        id='ID',
        short_desc='Short description',
        long_desc='Long description',
        price='Monthly price',
        primary='Is primary',
    )
    column_descriptions = dict(
        price='USD',
        primary='Primary tiers are displayed first',
    )
    column_list = ('id', 'name', 'price', 'primary',)
    form_columns = ('name', 'price', 'short_desc', 'long_desc', 'primary',)

    def __init__(self, session, **kwargs):
        super(TierAdminView, self).__init__(Tier, session, name='Tiers', **kwargs)
