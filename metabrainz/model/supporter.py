from metabrainz.model import db
from brainzutils.mail import send_mail
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

SUPPORTER_STATES = [
    STATE_ACTIVE,
    STATE_PENDING,
    STATE_WAITING,
    STATE_REJECTED,
    STATE_LIMITED,
]


class Supporter(db.Model, UserMixin):
    """Supporter model is used for supporters of MetaBrainz services like Live Data Feed.

    Supporters are either commercial or non-commercial (see `is_commercial`). Their
    access to the API is determined by their `state` (active, pending, waiting,
    or rejected). All non-commercial supporters have active state by default, but
    commercial supporters need to be approved by one of the admins first.
    """
    __tablename__ = 'supporter'

    # Common columns used by both commercial and non-commercial supporters:
    id = db.Column(db.Integer, primary_key=True)
    is_commercial = db.Column(db.Boolean, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL", onupdate="CASCADE"), unique=True)
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

    # Columns specific to commercial supporters:
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
    # good_standing for commercial supporters means they are paid up. For non-commercial supporters they are verified to be non-commercial.
    # the default value for this column has been changed to False, and once everything is cool, the supporter will be marked True
    good_standing = db.Column(db.Boolean, nullable=False, default=False)
    in_deadbeat_club = db.Column(db.Boolean, nullable=False, default=False)
    featured = db.Column(db.Boolean, nullable=False, default=False)

    tokens = db.relationship("Token", backref="owner", lazy="dynamic")
    token_log_records = db.relationship("TokenLog", back_populates="supporter", lazy="dynamic")

    datasets = db.relationship("Dataset", secondary="dataset_supporter")

    user = db.relationship("User", uselist=False, back_populates="supporter")

    def __str__(self):
        if self.is_commercial:
            return "%s (#%s)" % (self.org_name, self.id)
        else:
            if self.user.name:
                return "#%s (MBID: %s)" % (self.id, self.user.name)
            else:
                return str(self.id)

    @property
    def token(self):
        return Token.get(owner_id=self.id, is_active=True)

    @classmethod
    def add(cls, **kwargs):
        new_supporter = cls(
            is_commercial=kwargs.pop('is_commercial'),
            contact_name=kwargs.pop('contact_name'),
            contact_email=kwargs.pop('contact_email'),
            data_usage_desc=kwargs.pop('data_usage_desc'),
            user=kwargs.pop('user'),
            datasets=kwargs.pop('datasets', []),

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
        new_supporter.state = STATE_ACTIVE if not new_supporter.is_commercial else STATE_PENDING
        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)
        db.session.add(new_supporter)
        db.session.commit()

        if new_supporter.is_commercial:
            send_supporter_signup_notification(new_supporter)

        return new_supporter

    @classmethod
    def get(cls, **kwargs):
        return cls.query.filter_by(**kwargs).first()

    @classmethod
    def get_all(cls, **kwargs):
        """Get all supporters that match provided filters, ordered by their creation time."""
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
        """Get list of featured supporters which is randomly sorted.

        Args:
            limit: Max number of supporters to return.
            in_deadbeat_club: Returns only supporters from deadbeat club if set to True.
            with_logos: True if need only supporters with logo URLs specified, False if
                only supporters without logo URLs, None if it's irrelevant.
            tier_id: Returns only supporters from tier with a specified ID.

        Returns:
            List of supporters according to filters described above.
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
        """Get list of supporters who are actively supporting us.

        Returns:
            List of supporters sorted by amount of monthly support
        """
        query = cls.query.filter(cls.is_commercial == True)
        query = query.filter(or_(cls.state == STATE_ACTIVE, cls.state == STATE_LIMITED))
        query = query.filter(cls.good_standing == True)
        query = query.filter(cls.amount_pledged > 0)

        return query.order_by(cls.amount_pledged.desc()).all()

    @classmethod
    def search(cls, value):
        """Search supporters by their org_name, contact_name,
        or contact_email.
        """
        query = cls.query.filter(or_(
            cls.org_name.ilike('%'+value+'%'),
            cls.contact_name.ilike('%'+value+'%'),
            cls.contact_email.ilike('%'+value+'%'),
        ))
        return query.limit(20).all()

    def generate_token(self):
        """Generates new access token for this supporter."""
        if self.state == STATE_ACTIVE:
            return Token.generate_token(self.id)
        else:
            raise InactiveSupporterException("Can't generate token for inactive supporter.")

    def update(self, **kwargs):
        contact_name = kwargs.pop('contact_name')
        if contact_name is not None:
            self.contact_name = contact_name
        contact_email = kwargs.pop('contact_email')
        if contact_email is not None:
            self.contact_email = contact_email
        datasets = kwargs.pop('datasets', None)
        if datasets is not None:
            self.datasets = datasets
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


def send_supporter_signup_notification(supporter):
    """Send notification to admin about new signed up commercial supporter."""
    pairs_list_to_string = lambda pairs_list: '\n'.join([
        '%s: %s' % (pair[0], pair[1]) for pair in pairs_list
    ])
    send_mail(
        subject="[MetaBrainz] New commercial supporter signed up",
        text=pairs_list_to_string([
            ('Organization name', supporter.org_name),
            ('Description', supporter.org_desc),
            ('Contact name', supporter.contact_name),
            ('Contact email', supporter.contact_email),

            ('Website URL', supporter.website_url),
            ('Logo image URL', supporter.org_logo_url),
            ('API URL', supporter.api_url),

            ('Street', supporter.address_street),
            ('City', supporter.address_city),
            ('State', supporter.address_state),
            ('Postal code', supporter.address_postcode),
            ('Country', supporter.address_country),

            ('Tier', str(supporter.tier)),
            ('Amount pledged', '$%s' % str(supporter.amount_pledged)),

            ('Data usage description', supporter.data_usage_desc),
        ]),
        recipients=current_app.config['NOTIFICATION_RECIPIENTS'],
    )


class InactiveSupporterException(Exception):
    pass


class SupporterAdminView(AdminModelView):
    column_labels = dict(
        id='ID',
        is_commercial='Commercial',
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
        datasets='Datasets'
    )
    column_descriptions = dict(
        featured='Indicates if this supporter is publicly displayed on the website. '
                 'If this is set, make sure to fill up information like '
                 'organization name, logo URL, descriptions, etc.',
        data_usage_desc='Short description of how our products are being used '
                        'by this supporter. Usually one sentence.',
        org_desc='Description of the organization (private).',
        tier='Optional tier that is used only for commercial supporters.',
        amount_pledged='USD',
        in_deadbeat_club='Indicates if this supporter refuses to support us.',
    )
    column_list = (
        'is_commercial', 'org_name', 'tier', 'featured',
        'good_standing', 'state', 'datasets'
    )
    form_columns = (
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
        super(SupporterAdminView, self).__init__(Supporter, session, name='All supporters', **kwargs)

    def after_model_change(self, form, supporter, is_created):
        if supporter.state != STATE_ACTIVE:
            Token.revoke_tokens(supporter.id)
