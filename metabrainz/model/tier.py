from metabrainz.model import db
from metabrainz.model.supporter import Supporter
from metabrainz.admin import AdminModelView


class Tier(db.Model):
    """This model defines tier of support that commercial supporters can sign up to."""
    __tablename__ = 'tier'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode, nullable=False)
    short_desc = db.Column(db.UnicodeText)
    long_desc = db.Column(db.UnicodeText)
    price = db.Column(db.Numeric(11, 2), nullable=False)  # per month

    # Supporters can sign up only to available tiers on their own. If tier is not
    # available, it should be hidden from the website.
    available = db.Column(db.Boolean, nullable=False, default=False)

    # Primary tiers are shown first on the signup page. Secondary plans (along
    # with repeating primary plans) are listed on the "view all tiers" page
    # that lists all available tiers.
    primary = db.Column(db.Boolean, nullable=False, default=False)

    supporters = db.relationship("Supporter", back_populates="tier", lazy="dynamic")

    def __str__(self):
        return "%s (#%s)" % (self.name, self.id)

    @classmethod
    def create(cls, **kwargs):
        new_tier = cls(
            name=kwargs.pop('name'),
            short_desc=kwargs.pop('short_desc', None),
            long_desc=kwargs.pop('long_desc', None),
            price=kwargs.pop('price'),
            available=kwargs.pop('available', False),
            primary=kwargs.pop('primary', False),
        )
        db.session.add(new_tier)
        db.session.commit()
        return new_tier

    @classmethod
    def get(cls, **kwargs):
        return cls.query.filter_by(**kwargs).first()

    @classmethod
    def get_available(cls, sort=False, sort_desc=False):
        """Returns list of tiers that are available for sign up.

        You can also sort returned list by price of the tier.
        """
        query = cls.query.filter(cls.available == True)
        if sort:
            query = query.order_by(cls.price.desc()) if sort_desc else \
                    query.order_by(cls.price.asc())
        return query.all()

    def get_featured_supporters(self, **kwargs):
        return Supporter.get_featured(tier_id=self.id, **kwargs)


class TierAdminView(AdminModelView):
    column_labels = dict(
        id='ID',
        short_desc='Short description',
        long_desc='Long description',
        price='Monthly price',
        primary='Primary',
    )
    column_descriptions = dict(
        price='USD',
        primary="Primary tiers are displayed first on tier selection pages.",
        available="Indicates if supporters can sign up to that tier on their own. "
                  "Tier will be hidden from the website if it's not available.",
    )
    column_list = ('id', 'name', 'price', 'primary', 'available',)
    form_columns = ('name', 'price', 'short_desc', 'long_desc', 'primary', 'available',)

    def __init__(self, session, **kwargs):
        super(TierAdminView, self).__init__(Tier, session, name='Tiers', **kwargs)
