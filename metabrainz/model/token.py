from metabrainz.model import db
from metabrainz.model import token_log
from metabrainz.model.token_log import TokenLog
from metabrainz.utils import generate_string
from datetime import datetime, timedelta, timezone

TOKEN_LENGTH = 40


class Token(db.Model):
    __tablename__ = 'token'

    value = db.Column(db.String, primary_key=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('supporter.id', ondelete="SET NULL", onupdate="CASCADE"))
    created = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))

    log_records = db.relationship(TokenLog, backref="token", lazy="dynamic")

    @classmethod
    def get(cls, **kwargs):
        return cls.query.filter_by(**kwargs).first()

    @classmethod
    def get_all(cls, **kwargs):
        return cls.query.filter_by(**kwargs).all()

    @classmethod
    def search_by_value(cls, value):
        return cls.query.filter(cls.value.like('%'+value+'%')).all()

    @classmethod
    def generate_token(cls, owner_id):
        """Generates new token for a specified supporter and revokes all other
        tokens owned by this supporter.

        Returns:
            Value of the new token.
        """
        if owner_id is not None:
            last_hour_q = cls.query.filter(
                cls.owner_id == owner_id,
                cls.created > datetime.now(timezone.utc) - timedelta(hours=1),
            )
            if last_hour_q.count() > 0:
                raise TokenGenerationLimitException("Can't generate more than one token per hour.")
            cls.revoke_tokens(owner_id)

        new_token = cls(
            value=generate_string(TOKEN_LENGTH),
            owner_id=owner_id,
        )
        db.session.add(new_token)
        db.session.commit()

        TokenLog.create_record(new_token.value, token_log.ACTION_CREATE)

        return new_token.value

    @classmethod
    def revoke_tokens(cls, owner_id):
        """Revokes all tokens owned by a specified supporter.

        Args:
            owner_id: ID of a supporter.
        """
        tokens = db.session.query(cls).filter(
            cls.owner_id == owner_id,
            cls.is_active == True
        )
        for token in tokens:
            token.revoke()

    @classmethod
    def is_valid(cls, token_value):
        """Checks if token exists and is active."""
        token = cls.get(value=token_value)
        return token and token.is_active

    def revoke(self):
        self.is_active = False
        db.session.commit()
        TokenLog.create_record(self.value, token_log.ACTION_DEACTIVATE)


class TokenGenerationLimitException(Exception):
    pass