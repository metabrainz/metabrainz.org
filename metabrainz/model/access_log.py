from metabrainz.model import db
from metabrainz.mail import send_mail
from datetime import datetime, timedelta
from flask import current_app

HOURLY_ALERT_THRESHOLD = 10  # Max number of requests that can be done before admins get an alert


class AccessLog(db.Model):
    """Access log is used for tracking requests to the API.

    Each request needs to be logged. Logging is done to keep track of number of
    requests in a fixed time frame. If there is an unusual number of requests
    being made in this time frame, some kind of action is taken. See
    implementation of this model for more details.
    """
    __tablename__ = 'access_log'

    token = db.Column(db.String, db.ForeignKey('token.value'), primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), primary_key=True, default=datetime.utcnow)

    @classmethod
    def create_record(cls, access_token):
        """Creates new access log record with a current timestamp.

        It also checks if `HOURLY_ALERT_THRESHOLD` is exceeded, alerts admins if
        that's the case.

        Args:
            access_token: Access token used to access the API.

        Returns:
            New access log record.
        """
        new_record = cls(token=access_token)
        db.session.add(new_record)
        db.session.commit()

        # Checking if HOURLY_ALERT_THRESHOLD is exceeded
        # FIXME(roman): There's a way to abuse this checking by creating new
        # token. Maybe we should limit token creation to only one per hour or longer?
        count = cls.query.filter(cls.timestamp > datetime.now() - timedelta(hours=1),
                                 cls.token == access_token).count()
        if count > HOURLY_ALERT_THRESHOLD:
            # FIXME(roman): There's probably no need to send an email notification
            # about every request after the first one.
            send_mail(
                subject="[MetaBrainz] Hourly access limit exceeded",
                text="Hourly access limit exceeded for token %s" % access_token,
                recipients=[current_app.config['MANAGER_EMAIL']],
            )

        return new_record
