from metabrainz.model import db
from metabrainz.model.admin_view import AdminView
from metabrainz.model.organization import Organization


class Tier(db.Model):
    """This model defines tier of support that people can sign up to."""
    __tablename__ = 'tier'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode, nullable=False)
    short_desc = db.Column(db.Unicode)
    long_desc = db.Column(db.Unicode)
    price = db.Column(db.Numeric(11, 2), nullable=False)  # per month
    available = db.Column(db.Boolean, nullable=False, default=False)  # Indicates if orgs can sign up to that on their own

    # Primary tiers are shown on the signup page. Secondary plans (along with
    # repeating primary plans) are listed on the "view all tiers" page that
    # lists everything.
    primary = db.Column(db.Boolean, nullable=False, default=False)

    organizations = db.relationship(Organization, backref='tier',
                                    order_by=Organization.name,
                                    lazy="dynamic")

    def __unicode__(self):
        return self.name

    @classmethod
    def get_tier(cls, id):
        return cls.query.filter(cls.id == id).first()

    @classmethod
    def get_all(cls):
        """Returns list of all tiers sorted by price."""
        return cls.query.order_by(cls.price).all()

    def get_featured_orgs(self):
        return self.organizations.filter(Organization.featured == True).all()


class TierAdminView(AdminView):
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
        available='Indicates if organizations can sign up to that tier on their own',
    )
    column_list = ('id', 'name', 'price', 'primary', 'available',)
    form_columns = ('name', 'price', 'short_desc', 'long_desc', 'primary', 'available',)

    def __init__(self, session, **kwargs):
        super(TierAdminView, self).__init__(Tier, session, name='Tiers', **kwargs)
