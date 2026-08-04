from typing import Any
from datetime import datetime, timezone
from uuid import uuid4
from flask import current_app
from flask_login import UserMixin
from sqlalchemy import Column, Integer, Identity, Text, DateTime, Index, func, or_, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped, validates

from metabrainz.model import db
from metabrainz.model.moderation_log import ModerationLog
from metabrainz.model.old_username import OldUsername
from metabrainz.model.webhook import Webhook, EVENT_USER_CREATED


class UsernameNotAllowedException(Exception):
    pass


class User(db.Model, UserMixin):
    __tablename__ = "user"

    id = Column(Integer, Identity(), primary_key=True)
    login_id = Column(UUID, nullable=False, unique=True, default=uuid4)
    name = Column(Text, nullable=False)
    password = Column(Text, nullable=False)  # TODO: add a constraint to ensure password is cleared when deleted field is set

    email = Column(Text)
    unconfirmed_email = Column(Text)
    email_confirmed_at = Column(DateTime(timezone=True))

    member_since = Column(DateTime(timezone=True), default=func.now())
    last_login_at = Column(DateTime(timezone=True), default=func.now())
    last_updated = Column(DateTime(timezone=True), default=func.now())

    deleted = Column(Boolean, nullable=False, default=False)
    is_blocked = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("user_name_unq_idx", func.lower(name), unique=True),
    )

    # Tracks until when the user's "remember me" login is expected to stay valid. This mirrors the
    # lifetime of the flask-login remember cookie set at login time and is None when the user did not
    # opt into being remembered (or after logout). It lets the OAuth2 token endpoint expose the user's
    # remember-me status to whitelisted clients.
    remember_me_until = Column(DateTime(timezone=True))

    supporter: Mapped["Supporter"] = relationship("Supporter", uselist=False, back_populates="user", lazy="joined")
    moderation_logs: Mapped[list["ModerationLog"]] = relationship(
        "ModerationLog", back_populates="user", foreign_keys="ModerationLog.user_id",
        order_by="desc(ModerationLog.timestamp)"
    )
    moderator_actions: Mapped[list["ModerationLog"]] = relationship("ModerationLog", back_populates="moderator", foreign_keys="ModerationLog.moderator_id")

    def get_id(self):
        return str(self.login_id)

    def get_user_id(self):
        return self.id

    def get_email_any(self):
        return self.email or self.unconfirmed_email

    def is_email_confirmed(self):
        return self.email is not None

    @classmethod
    def confirmed_email_exists(cls, email, exclude_user_id=None):
        # case insensitively, because mailboxes are: an exact match let
        # 'Bob@x.com' past a guard that 'bob@x.com' would have tripped, leaving
        # two confirmed rows for the one mailbox
        email = (email or "").strip()
        if not email:
            return False
        query = cls.query.filter(func.lower(cls.email) == email.lower())
        if exclude_user_id is not None:
            query = query.filter(cls.id != exclude_user_id)
        return query.first() is not None

    @classmethod
    def get_others_using_email(cls, email, exclude_user_id=None, limit=10):
        """ Accounts other than ``exclude_user_id`` holding this address, confirmed or pending.

        Nothing stops two accounts sharing an address, so this is only ever
        used to warn about it, never to reject a change.
        """
        # the address reaches this from a JSON body, so it need not be a string
        email = email.strip() if isinstance(email, str) else ""
        if not email:
            return []
        query = cls.query.filter(
            cls.deleted.is_(False),
            or_(
                func.lower(cls.email) == email.lower(),
                func.lower(cls.unconfirmed_email) == email.lower(),
            ),
        )
        if exclude_user_id is not None:
            query = query.filter(cls.id != exclude_user_id)
        return query.order_by(cls.name).limit(limit).all()

    def change_email(self, moderator, new_email, confirmed, reason=None):
        """ Change this user's email address on a moderator's behalf.

        ``confirmed`` records whether the moderator vouches for the address. If
        they do it becomes the account's email immediately; otherwise it is
        stored as a pending address and any already confirmed one keeps working
        until the user follows a verification link, which is what happens when
        a user changes their own email.

        Returns whether the confirmed address changed, so the caller knows
        whether downstream needs to hear about it.
        """
        new_email = new_email.strip()
        old_email = self.email
        changed_at = datetime.now(timezone.utc)

        if confirmed:
            self.email = new_email
            # drop any pending address: it is superseded, and leaving it behind
            # would let a stale verification link overwrite what was just set
            self.unconfirmed_email = None
            self.email_confirmed_at = changed_at
        else:
            self.unconfirmed_email = new_email
        self.last_updated = changed_at

        status = "confirmed" if confirmed else "pending verification"
        log_message = f"Email changed to '{new_email}' ({status})."
        if reason:
            log_message += f" {reason}"
        self.moderate(moderator, "change_email", log_message)

        return confirmed and old_email != new_email

    def is_active(self):
        return not self.is_blocked

    def update_remember_me(self, remember: bool):
        """ Record whether the user opted into being remembered at login."""
        if remember:
            duration = current_app.config.get("REMEMBER_COOKIE_DURATION")
            self.remember_me_until = datetime.now(timezone.utc) + duration
        else:
            self.remember_me_until = None

    def has_active_remember_me(self) -> bool:
        """ Whether the user currently has an active, unexpired remember-me login. """
        if self.remember_me_until is None:
            return False
        return self.remember_me_until > datetime.now(timezone.utc)

    @staticmethod
    def normalize_name(name):
        return name.strip() if isinstance(name, str) else name

    @validates("name")
    def _normalize_name(self, key, name):
        return self.normalize_name(name)

    @classmethod
    def add(cls, **kwargs):
        from metabrainz import bcrypt

        name = cls.normalize_name(kwargs.pop("name"))
        if OldUsername.get(name) is not None:
            raise UsernameNotAllowedException()

        password = kwargs.pop("password")
        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        unconfirmed_email = kwargs.pop("unconfirmed_email", None)
        if not unconfirmed_email or not unconfirmed_email.strip():
            raise ValueError("Email address is required.")

        new_user = cls(name=name, password=password_hash, unconfirmed_email=unconfirmed_email)
        if kwargs:
            raise TypeError("Unexpected **kwargs: %r" % (kwargs,))

        db.session.add(new_user)
        return new_user

    @classmethod
    def _get(cls, filters: dict):
        filters = filters.copy()
        query = cls.query
        if "name" in filters:
            name = filters.pop("name")
            query = query.filter(func.lower(cls.name) == func.lower(name))
        return query.filter_by(**filters).first()

    @classmethod
    def get(cls, **kwargs):
        row = cls._get(kwargs)
        if row:
            return row

        if "email" in kwargs:
            unconfirmed_email_kwargs = kwargs.copy()
            # check for email column was already performed and a matching user not found,
            # so now check with unconfirmed email.
            unconfirmed_email_kwargs["unconfirmed_email"] = unconfirmed_email_kwargs.pop("email")
            return cls._get(unconfirmed_email_kwargs)

        return None

    def moderate(self, moderator, action, reason):
        """Moderate the user account"""
        log = ModerationLog(
            user_id=self.id,
            moderator_id=moderator.id,
            action=action,
            reason=reason
        )
        db.session.add(log)

    def block(self, moderator, reason):
        """Block the user account"""
        if self.is_blocked:
            raise ValueError("User is already blocked")
        self.is_blocked = True
        self.login_id = uuid4()

        self.moderate(moderator, "block", reason)

    def unblock(self, moderator, reason):
        """Unblock the user account"""
        if not self.is_blocked:
            raise ValueError("User is not blocked")
        self.is_blocked = False

        self.moderate(moderator, "unblock", reason)

    def verify_email_manually(self, moderator, reason):
        """Manually verify the user's email address"""
        if not self.unconfirmed_email:
            if self.is_email_confirmed():
                raise ValueError("User's email is already verified")
            else:
                raise ValueError("No email address to verify")
        if self.confirmed_email_exists(self.unconfirmed_email, exclude_user_id=self.id):
            raise ValueError("The email is already associated with an another account.")

        # Move unconfirmed email to confirmed email
        verified_at = datetime.now(timezone.utc)
        self.email = self.unconfirmed_email
        self.unconfirmed_email = None
        self.email_confirmed_at = verified_at
        self.last_updated = verified_at

        self.moderate(moderator, "verify_email", reason)

    def delete(self, moderator=None, reason=None):
        """Mark the user as deleted and store the username in old_username table.
        
        Args:
            moderator: Optional, the moderator performing the deletion
            reason: Optional, the reason for deletion
        """
        if self.deleted:
            raise ValueError("User is already deleted")

        deleted_username = OldUsername(username=self.name)
        db.session.add(deleted_username)
        
        self.deleted = True
        self.name = f"deleted-{self.id}"
        self.email = None
        self.unconfirmed_email = None
        self.password = ""
        self.login_id = uuid4()

        if moderator is not None and reason is not None:
            self.moderate(moderator, "delete", reason)

    def emit_event(self, event, **extras):
        """Emit an event for the user.

            This method internally commits the changes to the database, hence be careful when using it
            to avoid breaking other transactions.
        """
        payload: dict[str, Any] = {
            "user_id": self.id,
        }
        if event == EVENT_USER_CREATED:
            payload["name"] = self.name
            payload["member_since"] = self.member_since.isoformat()
        payload.update(extras)
        Webhook.create_delivery_for_event(event, payload)
