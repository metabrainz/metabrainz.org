from metabrainz.model import db
from metabrainz.model.admin_view import AdminView
from metabrainz.model.user import User


class Tier(db.Model):
    """This model defines tier of support that commercial users can sign up to."""
    __tablename__ = 'tier'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode, nullable=False)
    short_desc = db.Column(db.Unicode)
    long_desc = db.Column(db.Unicode)
    price = db.Column(db.Numeric(11, 2), nullable=False)  # per month

    # Indicates if users can sign up to that on their own
    available = db.Column(db.Boolean, nullable=False, default=False)

    # Primary tiers are shown on the signup page. Secondary plans (along with
    # repeating primary plans) are listed on the "view all tiers" page that
    # lists everything.
    primary = db.Column(db.Boolean, nullable=False, default=False)

    users = db.relationship("User", backref='tier', lazy="dynamic")

    def __unicode__(self):
        return "%s (#%s)" % (self.name, self.id)

    @classmethod
    def get(cls, **kwargs):
        return cls.query.filter_by(**kwargs).first()

    @classmethod
    def get_all(cls):
        """Returns list of all tiers sorted by price."""
        return cls.query.order_by(cls.price).all()

    @classmethod
    def get_available(cls):
        """Returns list of tiers that are available for sign up."""
        return cls.query.filter(cls.available == True).all()

    def get_featured_users(self):
        return self.users.filter(User.featured == True).all()


class TierAdminView(AdminView):
    column_labels = dict(
        id='ID',
        short_desc='Short description',
        long_desc='Long description',
        price='Monthly price',
        primary='Primary',
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
