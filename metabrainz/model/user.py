from sqlalchemy.sql.expression import func
from sqlalchemy.dialects import postgres
from flask_login import UserMixin
from flask import current_app
from metabrainz.model import db
from metabrainz.model.admin_view import AdminView
from metabrainz.model.token import Token
from metabrainz.model.tier import Tier
from metabrainz.mail import send_mail
from datetime import datetime


STATE_ACTIVE = "active"
STATE_PENDING = "pending"
STATE_REJECTED = "rejected"


class User(db.Model, UserMixin):
    """User model is used for users of MetaBrainz services like Live Data Feed.

    Users are ether commercial or non-commercial (see `is_commercial`). Their access to the API is
    determined by their `state` (active, pending, or rejected). All non-commercial users have
    active state by default, but commercial users need to be approved by one of the admins first.
    """
    __tablename__ = 'user'

    # Common columns used by both commercial and non-commercial users:
    id = db.Column(db.Integer, primary_key=True)
    is_commercial = db.Column(db.Boolean, nullable=False)
    musicbrainz_id = db.Column(db.Unicode, unique=True)  # MusicBrainz account that manages this user
    created = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    state = db.Column(postgres.ENUM(STATE_ACTIVE, STATE_PENDING, STATE_REJECTED, name='state_types'),
                      nullable=False)
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
    tier_id = db.Column(db.Integer, db.ForeignKey('tier.id', ondelete="SET NULL", onupdate="CASCADE"))
    payment_method = db.Column(db.Unicode)

    # Administrative columns:
    good_standing = db.Column(db.Boolean, nullable=False, default=True)
    is_approved = db.Column(db.Boolean, nullable=False, default=False)
    featured = db.Column(db.Boolean, nullable=False, default=False)

    tokens = db.relationship("Token", backref='user', lazy="dynamic")

    @property
    def token(self):
        return Token.get(owner=self.id, is_active=True)

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
        new_user.state = STATE_ACTIVE if not new_user.is_commercial else STATE_PENDING
        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)
        db.session.add(new_user)
        db.session.commit()

        if new_user.is_commercial:
            send_user_signup_notification(new_user)

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

    def generate_token(self):
        """Generates new access token for this user."""
        if self.state == STATE_ACTIVE:
            return Token.generate_token(self.id)
        else:
            raise InactiveUserException


def send_user_signup_notification(user):
    """Send notification to admin about new signed up commercial user."""
    pairs_list_to_string = lambda pairs_list: '\n'.join([
        '%s: %s' % (pair[0], pair[1]) for pair in pairs_list
    ])
    send_mail(
        subject="[MetaBrainz] New commercial user signed up",
        text=pairs_list_to_string([
            ('Organization name', user.org_name),
            ('Contact name', user.contact_name),
            ('Contact email', user.contact_email),

            ('Website URL', user.website_url),
            ('Logo image URL', user.org_logo_url),
            ('API URL', user.api_url),

            ('Street', user.address_street),
            ('City', user.address_city),
            ('State', user.address_state),
            ('Postal code', user.address_postcode),
            ('Country', user.address_country),

            ('Tier', '#%s - %s' % (user.tier_id, Tier.get(id=user.tier_id))),
            ('Payment method', user.payment_method),

            ('Usage description', user.description),
        ]),
        recipients=[current_app.config['MANAGER_EMAIL']],
    )


class InactiveUserException(Exception):
    pass


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
    column_list = (
        'is_commercial', 'musicbrainz_id', 'org_name', 'tier', 'featured',
        'good_standing', 'state',
    )
    form_columns = (
        'org_name', 'tier', 'good_standing', 'featured', 'org_logo_url', 'website_url',
        'description', 'api_url', 'contact_name', 'contact_email', 'address_street',
        'address_city', 'address_state', 'address_postcode', 'address_country',
        'is_commercial', 'musicbrainz_id', 'state',
    )

    def __init__(self, session, **kwargs):
        super(UserAdminView, self).__init__(User, session, name='Users', **kwargs)

    def after_model_change(self, form, user, is_created):
        if user.state != STATE_ACTIVE:
            Token.revoke_tokens(user.id)
