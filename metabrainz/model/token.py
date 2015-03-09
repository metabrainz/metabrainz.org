from metabrainz.model import db
from metabrainz.utils import generate_string

TOKEN_LENGTH = 40


class Token(db.Model):
    __tablename__ = 'token'

    value = db.Column(db.String, primary_key=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    owner = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="SET NULL", onupdate="CASCADE"))

    @classmethod
    def get(cls, **kwargs):
        return cls.query.filter_by(**kwargs).first()

    @classmethod
    def generate_token(cls, owner):
        """Generates new token for a specified user and revokes all other
        tokens owned by this user.

        Returns:
            Value of the new token.
        """
        cls.revoke_tokens(owner)

        new_token = cls(
            value=generate_string(TOKEN_LENGTH),
            owner=owner,
        )
        db.session.add(new_token)
        db.session.commit()

        return new_token.value

    @classmethod
    def revoke_tokens(cls, owner):
        """Revokes all tokens owned by a specified user.

        Args:
            owner: ID of a user.
        """
        db.session.query(cls).filter(cls.owner == owner) \
            .update({'is_active': False})
        db.session.commit()

    @classmethod
    def is_valid(cls, token_value):
        """Checks if token exists and is active."""
        token = cls.get(value=token_value)
        return token and token.is_active
