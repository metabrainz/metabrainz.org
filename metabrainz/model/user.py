from metabrainz.model import db
from metabrainz.model.admin_view import AdminView
from sqlalchemy.sql.expression import func
from flask_login import UserMixin


class User(db.Model, UserMixin):
    # TODO: Write docstring explaining who's a user.
    __tablename__ = 'user'

    # Common columns used by both commercial and non-commercial users:
    id = db.Column(db.Integer, primary_key=True)
    is_commercial = db.Column(db.Boolean, nullable=False)
    musicbrainz_id = db.Column(db.Unicode, unique=True)  # MusicBrainz account that manages this user
    contact_name = db.Column(db.Unicode, nullable=False)
    contact_email = db.Column(db.Unicode, nullable=False)
    description = db.Column(db.Unicode)  # Description of how data is being used by this user

    # Columns specific to commercial users:
    org_name = db.Column(db.Unicode)
    org_logo_url = db.Column(db.Unicode)
    website_url = db.Column(db.Unicode)
    api_url = db.Column(db.Unicode)
    address_street = db.Column(db.Unicode)
    address_city = db.Column(db.Unicode)
    address_state = db.Column(db.Unicode)
    address_postcode = db.Column(db.Unicode)
    address_country = db.Column(db.Unicode)
    tier_id = db.Column(db.Integer, db.ForeignKey('tier.id'))
    payment_method = db.Column(db.Unicode)

    # Administrative columns:
    good_standing = db.Column(db.Boolean, nullable=False, default=True)
    is_approved = db.Column(db.Boolean, nullable=False, default=False)
    featured = db.Column(db.Boolean, nullable=False, default=False)

    def __unicode__(self):
        return self.name

    @classmethod
    def add(cls, **kwargs):
        new_user = cls(
            is_commercial=kwargs.pop('is_commercial'),
            musicbrainz_id=kwargs.pop('musicbrainz_id'),
            contact_name=kwargs.pop('contact_name'),
            contact_email=kwargs.pop('contact_email'),
            description=kwargs.pop('description'),

            org_name=kwargs.pop('org_name', None),
            org_logo_url=kwargs.pop('org_logo_url', None),
            website_url=kwargs.pop('website_url', None),
            api_url=kwargs.pop('api_url', None),

            address_street=kwargs.pop('address_street', None),
            address_city=kwargs.pop('address_city', None),
            address_state=kwargs.pop('address_state', None),
            address_postcode=kwargs.pop('address_postcode', None),
            address_country=kwargs.pop('address_country', None),

            tier_id=kwargs.pop('tier_id', None),
            payment_method=kwargs.pop('payment_method', None),
        )
        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)
        db.session.add(new_user)
        db.session.commit()
        return new_user

    @classmethod
    def get(cls, **kwargs):
        return cls.query.filter_by(**kwargs).first()

    @classmethod
    def get_all(cls):
        """Returns list of all organizations."""
        return cls.query.all()

    @classmethod
    def get_featured(cls, limit=4):
        return cls.query.filter(cls.featured).order_by(func.random()).limit(limit).all()


class UserAdminView(AdminView):
    column_labels = dict(
        id='ID',
        is_commercial='Commercial',
        musicbrainz_id='MusicBrainz ID',
        org_logo_url='Logo URL',
        website_url='Homepage URL',
        api_url='API page URL',
        contact_name='Contact name',
        email='Email',
        address_street='Street',
        address_city='City',
        address_state='State',
        address_postcode='Postal code',
        address_country='Country',
    )
    column_descriptions = dict(
        description='How organization uses MetaBrainz projects',
    )
    column_list = ('is_commercial', 'musicbrainz_id', 'org_name', 'tier', 'featured', 'good_standing')
    form_columns = (
        'org_name', 'tier', 'good_standing', 'featured', 'org_logo_url', 'website_url',
        'description', 'api_url', 'contact_name', 'contact_email', 'address_street',
        'address_city', 'address_state', 'address_postcode', 'address_country',
        'is_commercial', 'musicbrainz_id',
    )

    def __init__(self, session, **kwargs):
        super(UserAdminView, self).__init__(User, session, name='Users', **kwargs)
