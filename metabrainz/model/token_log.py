from metabrainz.model import db
from flask_login import current_user
from datetime import datetime

ACTION_DEACTIVATE = 'deactivate'
ACTION_CREATE = 'create'


class TokenLog(db.Model):
    """TokenLog class is used for logging changes to access tokens."""
    __tablename__ = 'token_log'

    token_value = db.Column(
        db.String,
        db.ForeignKey('token.value'),
        primary_key=True,
    )
    timestamp = db.Column(
        db.DateTime(timezone=True),
        primary_key=True,
        default=datetime.utcnow,
    )
    action = db.Column(
        db.Enum(
            ACTION_DEACTIVATE,
            ACTION_CREATE,
            name='token_log_action_types'
        ),
        primary_key=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete="SET NULL", onupdate="CASCADE"),
        nullable=False,
    )

    @classmethod
    def create_record(cls, access_token, action):
        new_record = cls(
            token_value=access_token,
            action=action,
            user_id=current_user.id,
        )
        db.session.add(new_record)
        db.session.commit()
        return new_record

    @classmethod
    def list(cls, limit=None):
        query = cls.query.order_by(cls.timestamp.desc())
        if limit:
            query = query.limit(limit)
        return query.all()
