from metabrainz.model import db
from metabrainz.model.token import Token
from metabrainz.model.supporter import Supporter
from brainzutils.mail import send_mail
from brainzutils import cache
from sqlalchemy import func, text
from sqlalchemy.dialects import postgresql
from datetime import datetime, timedelta
from flask import current_app
import logging
import pytz

CLEANUP_RANGE_MINUTES = 60
DIFFERENT_IP_LIMIT = 50


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
    ip_address = db.Column(postgresql.INET)

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
            email = db.session \
                .query(Supporter.contact_email) \
                .join(Token) \
                .filter(Token.value == access_token) \
                .first()
            msg = ("Hourly access threshold exceeded for token %s\n\n"
                   "The supporter associated with the token can be contacted at %s\n\n"
                   "This token has been used from %s different IP "
                   "addresses during the last %s minutes.") % \
                  (access_token, email, count, CLEANUP_RANGE_MINUTES)
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
    def get_hourly_usage(cls, supporter_id=None):
        """Get information about API usage.

        Args:
            supporter_id: Supporter ID that can be specified to get stats only for that account.

        Returns:
            List of <datetime, request count> tuples for every hour.
        """
        if not supporter_id:
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
                'JOIN supporter ON token.owner_id = supporter.id '
                'WHERE supporter.id = %s '
                'GROUP BY extract(year from "timestamp"), extract(month from "timestamp"), '
                '         extract(day from "timestamp"), trunc(extract(hour from "timestamp")) '
                'ORDER BY ts',
                (supporter_id,)
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
    def active_supporter_count(cls):
        """Returns number of different supporters whose access has been logged in
        the last 24 hours.
        """
        return cls.query.join(Token).join(Supporter) \
            .filter(cls.timestamp > datetime.now() - timedelta(days=1)) \
            .distinct(Supporter.id).count()

    @classmethod
    def top_downloaders(cls, limit=None):
        """Generates list of most active supporters in the last 24 hours.

        Args:
            limit: Max number of items to return.

        Returns:
            List of <Supporter, request count> pairs
        """
        query = db.session.query(Supporter).join(Token).join(AccessLog) \
            .filter(cls.timestamp > datetime.now() - timedelta(days=1)) \
            .add_columns(func.count("AccessLog.*").label("count")).group_by(Supporter.id) \
            .order_by(text("count DESC"))
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def top_ips(cls, days=7, limit=None):
        """
            Generates two list of most active ip addresses in the last days. One
            list for commercial supporters and another list for non-commercial supporters who
            are not in good standing. good standing for non-commercial supporters means
            that they are verified good non-commercial supporters.

        Args:
            days: Number of past days to include in the query
            limit: Max number of items to return.

        Returns:
            Tuple of (non_commercial, commercial) lists of [ip_address, token, supporter_id, contact_name, contact_email]

        """
        query = db.session.query(AccessLog) \
                          .select_from(AccessLog) \
                          .join(Token) \
                          .join(Supporter) \
                          .with_entities(AccessLog.ip_address, AccessLog.token, Supporter.id, \
                                         Supporter.contact_name, Supporter.contact_email, Supporter.data_usage_desc) \
                          .filter(Supporter.is_commercial == False) \
                          .filter(cls.timestamp > datetime.now() - timedelta(days=days)) \
                          .filter(Supporter.good_standing != True) \
                          .add_columns(func.count("AccessLog.*").label("count")) \
                          .group_by(AccessLog.ip_address, AccessLog.token, Supporter.id, \
                                    Supporter.contact_name, Supporter.contact_email, Supporter.data_usage_desc) \
                            .order_by(text("count DESC"))
        if limit:
            query = query.limit(limit)
        non_commercial = query.all()

        query = db.session.query(AccessLog) \
                          .select_from(AccessLog) \
                          .join(Token) \
                          .join(Supporter) \
                          .with_entities(AccessLog.ip_address, AccessLog.token, Supporter.id, \
                                         Supporter.contact_name, Supporter.contact_email, Supporter.data_usage_desc) \
                          .filter(Supporter.is_commercial == True) \
                          .filter(cls.timestamp > datetime.now() - timedelta(days=days)) \
                          .add_columns(func.count("AccessLog.*").label("count")) \
                          .group_by(AccessLog.ip_address, AccessLog.token, Supporter.id, \
                                    Supporter.contact_name, Supporter.contact_email, Supporter.data_usage_desc) \
                          .order_by(text("count DESC"))
        if limit:
            query = query.limit(limit)
        commercial = query.all()

        return (non_commercial, commercial)


    @classmethod
    def top_tokens(cls, days=7, limit=None):
        """
            Generates two list of the most active token in the last days. One
            list for commercial supporters and another list for non-commercial supporters who
            are not in good standing. Good standing for non-commercial supporters means
            that they are verified good non-commercial supporters.

        Args:
            days: Number of past days to include in the query
            limit: Max number of items to return.

        Returns:
            Tuple of (non_commercial, commercial) lists of [token, musicbrainz_id, supporter_id, contact_name, contact_email]

        """
        query = db.session.query(AccessLog) \
                          .select_from(AccessLog) \
                          .join(Token).join(Supporter) \
                          .with_entities(AccessLog.token, Supporter.id, Supporter.contact_name, \
                                         Supporter.contact_email) \
                          .filter(Supporter.is_commercial == False) \
                          .filter(cls.timestamp > datetime.now() - timedelta(days=days)) \
                          .filter(Supporter.good_standing != True) \
                          .add_columns(func.count("AccessLog.*").label("count")) \
                          .group_by(AccessLog.token, Supporter.id, Supporter.contact_name, Supporter.contact_email) \
                          .order_by(text("count DESC"))
        if limit:
            query = query.limit(limit)
        non_commercial = query.all()

        query = db.session.query(AccessLog) \
                          .select_from(AccessLog) \
                          .join(Token).join(Supporter) \
                          .with_entities(AccessLog.token, Supporter.id, Supporter.contact_name, Supporter.contact_email) \
                          .filter(Supporter.is_commercial == True) \
                          .filter(cls.timestamp > datetime.now() - timedelta(days=days)) \
                          .add_columns(func.count("AccessLog.*").label("count")) \
                          .group_by(AccessLog.token, Supporter.id, Supporter.contact_name, Supporter.contact_email) \
                          .order_by(text("count DESC"))
        if limit:
            query = query.limit(limit)
        commercial = query.all()

        return (non_commercial, commercial)
