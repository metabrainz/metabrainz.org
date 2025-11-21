from flask_admin.contrib.sqla.form import InlineOneToOneModelConverter
from flask_admin.model import InlineFormAdmin
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import contains_eager, relationship, mapped_column
from sqlalchemy.orm.attributes import Mapped

from metabrainz.model import db
from brainzutils.mail import send_mail
from metabrainz.model.token import Token
from metabrainz.admin import AdminModelView
from sqlalchemy.sql.expression import func, or_
from sqlalchemy.dialects import postgresql
from flask import current_app
from datetime import datetime

from metabrainz.model.user import User

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


class Supporter(db.Model):
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
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="SET NULL", onupdate="CASCADE"), unique=True)
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
    tier = db.relationship("Tier", uselist=False, back_populates="supporters")
    user: Mapped["User"] = relationship("User", uselist=False, back_populates="supporter", lazy="joined")

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
            data_usage_desc=kwargs.pop('data_usage_desc'),
            user=kwargs.pop('user'),
            datasets=kwargs.pop('datasets', []),

            contact_name=kwargs.pop('contact_name'),
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
    def get_all_commercial(cls, limit=None, offset=None, state=None, featured=None, good_standing=None, search=None):
        query = cls.query.filter(cls.is_commercial==True)

        if state:
            query = query.filter(cls.state == state)
        if featured is not None:
            query = query.filter(cls.featured == featured)
        if good_standing is not None:
            query = query.filter(cls.good_standing == good_standing)
        if search:
            # Search across multiple fields
            from sqlalchemy import or_
            search_term = f"%{search}%"
            query = query.join(User).filter(
                or_(
                    cls.org_name.ilike(search_term),
                    cls.contact_name.ilike(search_term),
                    User.name.ilike(search_term),
                    User.email.ilike(search_term)
                )
            )

        query = query.order_by(cls.org_name)
        count = query.count()  # Total count should be calculated before limits
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
        return query.all(), count

    @classmethod
    def get_all_with_filters(cls, limit=None, offset=None, state=None, is_commercial=None,
                            featured=None, good_standing=None, search=None):
        """Get all supporters with optional filters and pagination.

        Args:
            limit: Maximum number of results to return
            offset: Number of results to skip
            state: Filter by supporter state (active, pending, waiting, rejected, limited)
            is_commercial: Filter by commercial status (True/False/None for all)
            featured: Filter by featured status (True/False/None for all)
            good_standing: Filter by good standing status (True/False/None for all)
            search: Search term to filter by org_name, contact_name, username, or email

        Returns:
            Tuple of (supporters_list, total_count)
        """
        query = cls.query

        if state:
            query = query.filter(cls.state == state)
        if is_commercial is not None:
            query = query.filter(cls.is_commercial == is_commercial)
        if featured is not None:
            query = query.filter(cls.featured == featured)
        if good_standing is not None:
            query = query.filter(cls.good_standing == good_standing)
        if search:
            # Search across multiple fields
            from sqlalchemy import or_
            search_term = f"%{search}%"
            query = query.join(User).filter(
                or_(
                    cls.org_name.ilike(search_term),
                    cls.contact_name.ilike(search_term),
                    User.name.ilike(search_term),
                    User.email.ilike(search_term)
                )
            )

        # Order by created date descending (most recent first)
        query = query.order_by(cls.created.desc())
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
        """ Search supporters by their org_name, name, or email. """
        return cls.query \
        .join(Supporter.user) \
        .options(contains_eager(Supporter.user)) \
        .filter(or_(
            cls.org_name.ilike('%'+value+'%'),
            cls.contact_name.ilike('%'+value+'%'),
            User.name.ilike('%'+value+'%'),
            User.email.ilike('%'+value+'%'),
        )) \
        .limit(20) \
        .all()

    def generate_token(self):
        """Generates new access token for this supporter."""
        if self.state == STATE_ACTIVE:
            return Token.generate_token(self.id)
        else:
            raise InactiveSupporterException("Can't generate token for inactive supporter.")

    def update(self, **kwargs):
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
        if old_state != self.state and not current_app.config["DEBUG"]:
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
                recipients=[self.user.email],
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
            ('Contact email', supporter.user.email),

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
