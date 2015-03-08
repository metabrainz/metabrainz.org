from metabrainz.model import db
from datetime import datetime


class AccessLog(db.Model):
    __tablename__ = 'access_log'

    token = db.Column(db.String, db.ForeignKey('token.value'), primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), primary_key=True, default=datetime.utcnow)
    packet_number = db.Column(db.Integer, nullable=False)

    @classmethod
    def create_record(cls, access_token, packet_number):
        """Creates new access log record with a current timestamp.

        Args:
            access_token: Access token used to access.
            packet_number: Number of the replication packet that has been requested.

        Returns:
            New access log record.
        """
        new_record = cls(
            token=access_token,
            packet_number=packet_number,
        )
        db.session.add(new_record)
        db.session.commit()
        return new_record
