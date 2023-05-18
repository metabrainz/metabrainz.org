from metabrainz.model import db
from flask_login import current_user
from datetime import datetime

ACTION_DEACTIVATE = 'deactivate'
ACTION_CREATE = 'create'


class TokenLog(db.Model):
    """TokenLog class is used for logging changes to access tokens."""
    __tablename__ = 'token_log'

    token_value = db.Column(db.String, db.ForeignKey('token.value'), primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), primary_key=True, default=datetime.utcnow)
    action = db.Column(
        db.Enum(
            ACTION_DEACTIVATE,
            ACTION_CREATE,
            name='token_log_action_types'
        ),
        primary_key=True,
    )
    supporter_id = db.Column("user_id", db.Integer, db.ForeignKey('user.id', ondelete="SET NULL", onupdate="CASCADE"))
    supporter = db.relationship("Supporter", back_populates="token_log_records")

    @classmethod
    def create_record(cls, access_token, action):
        supporter_id = current_user.id if current_user.is_authenticated else None
        new_record = cls(
            token_value=access_token,
            action=action,
            supporter_id=supporter_id,
        )
        db.session.add(new_record)
        db.session.commit()
        return new_record

    @classmethod
    def list(cls, limit=None, offset=None):
        query = cls.query.order_by(cls.timestamp.desc())
        count = query.count()  # Total count should be calculated before limits
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
        return query.all(), count
