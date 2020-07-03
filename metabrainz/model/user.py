from metabrainz.model import db
from metabrainz.mail import send_mail
from metabrainz.model.token import Token
from metabrainz.admin import AdminModelView
from sqlalchemy.sql.expression import func, or_
from sqlalchemy.dialects import postgresql
from flask_login import UserMixin
from flask import current_app
from datetime import datetime


STATE_ACTIVE = "active"
STATE_PENDING = "pending"
STATE_WAITING = "waiting"
STATE_REJECTED = "rejected"
STATE_LIMITED = "limited"

USER_STATES = [
    STATE_ACTIVE,
    STATE_PENDING,
    STATE_WAITING,
    STATE_REJECTED,
    STATE_LIMITED,
]


class User(db.Model, UserMixin):
    """User model is used for users of MetaBrainz services like Live Data Feed.

    Users are either commercial or non-commercial (see `is_commercial`). Their
    access to the API is determined by their `state` (active, pending, waiting,
    or rejected). All non-commercial users have active state by default, but
    commercial users need to be approved by one of the admins first.
    """
    __tablename__ = 'user'

    # Common columns used by both commercial and non-commercial users:
    id = db.Column(db.Integer, primary_key=True)
    is_commercial = db.Column(db.Boolean, nullable=False)
    musicbrainz_id = db.Column(db.Unicode, unique=True)  # MusicBrainz account that manages this user
    created = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    state = db.Column(postgresql.ENUM(
        STATE_ACTIVE,
        STATE_PENDING,
        STATE_WAITING,
        STATE_REJECTED,
        STATE_LIMITED,
        name='state_types'
    ), nullable=False)
    contact_name = db.Column(db.Unicode, nullable=False)
    contact_email = db.Column(db.Unicode, nullable=False)
    data_usage_desc = db.Column(db.UnicodeText)

    # Columns specific to commercial users:
    org_name = db.Column(db.Unicode)
    logo_filename = db.Column(db.Unicode)
    org_logo_url = db.Column(db.Unicode)
    website_url = db.Column(db.Unicode)
    api_url = db.Column(db.Unicode)
    org_desc = db.Column(db.UnicodeText)
    address_street = db.Column(db.Unicode)
    address_city = db.Column(db.Unicode)
    address_state = db.Column(db.Unicode)
    address_postcode = db.Column(db.Unicode)
    address_country = db.Column(db.Unicode)
    tier_id = db.Column(db.Integer, db.ForeignKey('tier.id', ondelete="SET NULL", onupdate="CASCADE"))
    amount_pledged = db.Column(db.Numeric(11, 2))

    # Administrative columns:
    # good_standing for commercial users means they are paid up. For non-commercial users they are verified to be non-commercial.
    # the default value for this column has been changed to False, and once everything is cool, the user will be marked True
    good_standing = db.Column(db.Boolean, nullable=False, default=False)
    in_deadbeat_club = db.Column(db.Boolean, nullable=False, default=False)
    featured = db.Column(db.Boolean, nullable=False, default=False)

    tokens = db.relationship("Token", backref="owner", lazy="dynamic")
    token_log_records = db.relationship("TokenLog", backref="user", lazy="dynamic")

    def __str__(self):
        if self.is_commercial:
            return "%s (#%s)" % (self.org_name, self.id)
        else:
            if self.musicbrainz_id:
                return "#%s (MBID: %s)" % (self.id, self.musicbrainz_id)
            else:
                return str(self.id)

    @property
    def token(self):
        return Token.get(owner_id=self.id, is_active=True)

    @classmethod
    def add(cls, **kwargs):
        new_user = cls(
            is_commercial=kwargs.pop('is_commercial'),
            musicbrainz_id=kwargs.pop('musicbrainz_id'),
            contact_name=kwargs.pop('contact_name'),
            contact_email=kwargs.pop('contact_email'),
            data_usage_desc=kwargs.pop('data_usage_desc'),
            org_desc=kwargs.pop('org_desc', None),

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
            amount_pledged=kwargs.pop('amount_pledged', None),
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
    def get_all(cls, **kwargs):
        """Get all users that match provided filters, ordered by their creation time."""
        return cls.query.filter_by(**kwargs).order_by(cls.created.desc()).all()

    @classmethod
    def get_all_commercial(cls, limit=None, offset=None):
        query = cls.query.filter(cls.is_commercial==True).order_by(cls.org_name)
        count = query.count()  # Total count should be calculated before limits
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
        return query.all(), count

    @classmethod
    def get_featured(cls, limit=None, **kwargs):
        """Get list of featured users which is randomly sorted.

        Args:
            limit: Max number of users to return.
            in_deadbeat_club: Returns only users from deadbeat club if set to True.
            with_logos: True if need only users with logo URLs specified, False if
                only users without logo URLs, None if it's irrelevant.
            tier_id: Returns only users from tier with a specified ID.

        Returns:
            List of users according to filters described above.
        """
        query = cls.query.filter(cls.featured == True)
        query = query.filter(cls.in_deadbeat_club == kwargs.pop('in_deadbeat_club', False))
        with_logos = kwargs.pop('with_logos', None)
        if with_logos:
            query = query.filter(cls.org_logo_url != None)
        tier_id = kwargs.pop('tier_id', None)
        if tier_id:
            query = query.filter(cls.tier_id == tier_id)
        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)
        return query.order_by(func.random()).limit(limit).all()

    @classmethod
    def get_active_supporters(cls):
        """Get list of users who are actively supporting us.

        Returns:
            List of users sorted by amount of monthly support
        """
        query = cls.query.filter(cls.is_commercial == True)
        query = query.filter(or_(cls.state == STATE_ACTIVE, cls.state == STATE_LIMITED))
        query = query.filter(cls.good_standing == True)
        query = query.filter(cls.amount_pledged > 0)

        return query.order_by(cls.amount_pledged.desc()).all()

    @classmethod
    def search(cls, value):
        """Search users by their musicbrainz_id, org_name, contact_name,
        or contact_email.
        """
        query = cls.query.filter(or_(
            cls.musicbrainz_id.ilike('%'+value+'%'),
            cls.org_name.ilike('%'+value+'%'),
            cls.contact_name.ilike('%'+value+'%'),
            cls.contact_email.ilike('%'+value+'%'),
        ))
        return query.limit(20).all()

    def generate_token(self):
        """Generates new access token for this user."""
        if self.state == STATE_ACTIVE:
            return Token.generate_token(self.id)
        else:
            raise InactiveUserException("Can't generate token for inactive user.")

    def update(self, **kwargs):
        contact_name = kwargs.pop('contact_name')
        if contact_name is not None:
            self.contact_name = contact_name
        contact_email = kwargs.pop('contact_email')
        if contact_email is not None:
            self.contact_email = contact_email
        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)
        db.session.commit()

    def set_state(self, state):
        old_state = self.state
        self.state = state
        db.session.commit()
        if old_state != self.state:
            # TODO: Send additional info about new state.
            state_name = "ACTIVE" if self.state == STATE_ACTIVE else \
                         "REJECTED" if self.state == STATE_REJECTED else \
                         "PENDING" if self.state == STATE_PENDING else \
                         "WAITING" if self.state == STATE_WAITING else \
                         "LIMITED" if self.state == STATE_LIMITED else \
                         self.state
            send_mail(
                subject="[MetaBrainz] Your account has been updated",
                text='State of your MetaBrainz account has been changed to "%s".' % state_name,
                recipients=[self.contact_email],
            )


def send_user_signup_notification(user):
    """Send notification to admin about new signed up commercial user."""
    pairs_list_to_string = lambda pairs_list: '\n'.join([
        '%s: %s' % (pair[0], pair[1]) for pair in pairs_list
    ])
    send_mail(
        subject="[MetaBrainz] New commercial user signed up",
        text=pairs_list_to_string([
            ('Organization name', user.org_name),
            ('Description', user.org_desc),
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

            ('Tier', str(user.tier)),
            ('Amount pledged', '$%s' % str(user.amount_pledged)),

            ('Data usage description', user.data_usage_desc),
        ]),
        recipients=current_app.config['NOTIFICATION_RECIPIENTS'],
    )


class InactiveUserException(Exception):
    pass


class UserAdminView(AdminModelView):
    column_labels = dict(
        id='ID',
        is_commercial='Commercial',
        musicbrainz_id='MusicBrainz ID',
        data_usage_desc='Data usage description',
        org_desc='Organization description',
        good_standing='Good standing',
        amount_pledged='Amount pledged',
        org_name='Organization name',
        org_logo_url='Organization logo URL',
        website_url='Organization homepage URL',
        api_url='Organization API page URL',
        contact_name='Contact name',
        contact_email='Email',
        address_street='Street',
        address_city='City',
        address_state='State',
        address_postcode='Postal code',
        address_country='Country',
        in_deadbeat_club='In Deadbeat Club',
    )
    column_descriptions = dict(
        featured='Indicates if this user is publicly displayed on the website. '
                 'If this is set, make sure to fill up information like '
                 'organization name, logo URL, descriptions, etc.',
        data_usage_desc='Short description of how our products are being used '
                        'by this user. Usually one sentence.',
        org_desc='Description of the organization (private).',
        tier='Optional tier that is used only for commercial users.',
        amount_pledged='USD',
        in_deadbeat_club='Indicates if this user refuses to support us.',
    )
    column_list = (
        'is_commercial', 'musicbrainz_id', 'org_name', 'tier', 'featured',
        'good_standing', 'state',
    )
    form_columns = (
        'musicbrainz_id',
        'contact_name',
        'contact_email',
        'state',
        'is_commercial',
        'good_standing',
        'tier',
        'amount_pledged',
        'org_name',
        'org_logo_url',
        'website_url',
        'api_url',
        'data_usage_desc',
        'org_desc',
        'in_deadbeat_club',
        'featured',
        'address_street',
        'address_city',
        'address_state',
        'address_postcode',
        'address_country',
    )

    def __init__(self, session, **kwargs):
        super(UserAdminView, self).__init__(User, session, name='All users', **kwargs)

    def after_model_change(self, form, user, is_created):
        if user.state != STATE_ACTIVE:
            Token.revoke_tokens(user.id)
