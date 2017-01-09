from metabrainz.model import db
from metabrainz.model.token import Token
from metabrainz.model.user import User
from metabrainz.mail import send_mail
from brainzutils import cache
from sqlalchemy import func
from sqlalchemy.dialects import postgres
from datetime import datetime, timedelta
from flask import current_app
import logging
import pytz

CLEANUP_RANGE_MINUTES = 60
DIFFERENT_IP_LIMIT = 25


class AccessLog(db.Model):
    """Access log is used for tracking requests to the API.

    Each request needs to be logged. Logging is done to keep track of number of
    requests in a fixed time frame. If there is an unusual number of requests
    being made from different IP addresses in this time frame, action is taken.
    See implementation of this model for more details.
    """
    __tablename__ = 'access_log'

    token = db.Column(db.String, db.ForeignKey('token.value'), primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), primary_key=True, default=datetime.utcnow)
    ip_address = db.Column(postgres.INET)

    @classmethod
    def create_record(cls, access_token, ip_address):
        """Creates new access log record with a current timestamp.

        It also checks if `DIFFERENT_IP_LIMIT` is exceeded within current time
        and `CLEANUP_RANGE_MINUTES`, alerts admins if that's the case.

        Args:
            access_token: Access token used to access the API.
            ip_address: IP access used to access the API.

        Returns:
            New access log record.
        """
        new_record = cls(
            token=access_token,
            ip_address=ip_address,
        )
        db.session.add(new_record)
        db.session.commit()

        # Checking if HOURLY_ALERT_THRESHOLD is exceeded
        count = cls.query \
            .distinct(cls.ip_address) \
            .filter(cls.timestamp > datetime.now(pytz.utc) - timedelta(minutes=CLEANUP_RANGE_MINUTES),
                    cls.token == access_token) \
            .count()
        if count > DIFFERENT_IP_LIMIT:
            msg = ("Hourly access threshold exceeded for token %s\n\n"
                   "This token has been used from %s different IP "
                   "addresses during the last %s minutes.") % \
                  (access_token, count, CLEANUP_RANGE_MINUTES)
            logging.info(msg)
            # Checking if notification for admins about this token abuse has
            # been sent in the last hour. This info is kept in cache.
            key = "alert_sent_%s" % access_token
            if not cache.get(key):
                send_mail(
                    subject="[MetaBrainz] Hourly access threshold exceeded",
                    recipients=current_app.config['NOTIFICATION_RECIPIENTS'],
                    text=msg,
                )
                cache.set(key, True, 3600)  # 1 hour

        return new_record

    @classmethod
    def remove_old_ip_addr_records(cls):
        cls.query. \
            filter(cls.timestamp < datetime.now(pytz.utc) - timedelta(minutes=CLEANUP_RANGE_MINUTES)). \
            update({cls.ip_address: None})
        db.session.commit()

    @classmethod
    def get_hourly_usage(cls, user_id=None):
        """Get information about API usage.

        Args:
            user_id: User ID that can be specified to get stats only for that account.

        Returns:
            List of <datetime, request count> tuples for every hour.
        """
        if not user_id:
            rows = db.engine.execute(
                'SELECT max("timestamp") as ts, count(*) '
                'FROM access_log '
                'GROUP BY extract(year from "timestamp"), extract(month from "timestamp"), '
                '         extract(day from "timestamp"), trunc(extract(hour from "timestamp")) '
                'ORDER BY ts'
            )
        else:
            rows = db.engine.execute(
                'SELECT max(access_log."timestamp") as ts, count(access_log.*) '
                'FROM access_log '
                'JOIN token ON access_log.token = token.value '
                'JOIN "user" ON token.owner_id = "user".id '
                'WHERE "user".id = %s '
                'GROUP BY extract(year from "timestamp"), extract(month from "timestamp"), '
                '         extract(day from "timestamp"), trunc(extract(hour from "timestamp")) '
                'ORDER BY ts',
                (user_id,)
            )
        return [(
            r[0].replace(
                minute=0,
                second=0,
                microsecond=0,
                tzinfo=None,
            ),
            r[1]
        ) for r in rows]

    @classmethod
    def active_user_count(cls):
        """Returns number of different users whose access has been logged in
        the last 24 hours.
        """
        return cls.query.join(Token).join(User) \
            .filter(cls.timestamp > datetime.now() - timedelta(days=1)) \
            .distinct(User.id).count()

    @classmethod
    def top_downloaders(cls, limit=None):
        """Generates list of most active users in the last 24 hours.

        Args:
            limit: Max number of items to return.

        Returns:
            List of <User, request count> pairs
        """
        query = db.session.query(User).join(Token).join(AccessLog) \
            .filter(cls.timestamp > datetime.now() - timedelta(days=1)) \
            .add_columns(func.count("AccessLog.*").label("count")).group_by(User.id) \
            .order_by("count DESC")
        if limit:
            query = query.limit(limit)
        return query.all()
