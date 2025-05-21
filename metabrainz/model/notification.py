from enum import Enum
import uuid

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from metabrainz.model import db



class NotificationProjectType(Enum):
    METABRAINZ = 'metabrainz'
    MUSICBRAINZ = 'musicbrainz'
    LISTENBRAINZ = 'listenbrainz'
    BOOKBRAINZ = 'bookbrainz'
    CRITIQUEBRAINZ = 'critiquebrainz'


class Notification(db.Model):
    """This model defines the notifications for metabrianz projects."""
    __tablename__='notification'

    id = db.Column(db.Integer, primary_key=True)
    musicbrainz_row_id = db.Column(db.Integer, nullable=False)
    project = db.Column(db.Enum(NotificationProjectType, name = 'notification_project_type'), nullable=False)
    read = db.Column(db.Boolean, default=False)
    created = db.Column(db.DateTime(timezone=True), default=func.now())
    expire_age = db.Column(db.SmallInteger, nullable=False)
    important = db.Column(db.Boolean, default=False)
    email_id = db.Column(db.Text, unique=True, default=str(uuid.uuid4()))
    subject = db.Column(db.Text)
    body = db.Column(db.Text)
    template_id = db.Column(db.Text)
    template_params = db.Column(JSONB)

    __table_args__=(
        db.CheckConstraint(
            """
            ((subject IS NOT NULL AND body IS NOT NULL) AND (template_id IS NULL AND template_params IS NULL))
            OR
            ((subject IS NULL AND body IS NULL) AND (template_id IS NOT NULL AND template_params IS NOT NULL))
            """,
            name='mail_type'
        ),
    )

    @classmethod
    def get(cls: "Notification", **kwargs) -> "Notification" | None:
        return cls.query.filter_by(**kwargs).first()
    
    @classmethod
    def create(cls: "Notification", **kwargs) -> "Notification":
        new_notification = cls(**kwargs)
        db.session.add(new_notification)
        db.session.commit()

        return new_notification
