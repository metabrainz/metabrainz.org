import hashlib

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import text

from metabrainz.model import db
from metabrainz.model.domain_blacklist import DomainBlacklist
from metabrainz.model.old_username import OldUsername
from metabrainz.model.user import User
from metabrainz.user.username import sanitize_username


def normalize_registration_username(username: str | None) -> str:
    return username.strip() if username else ""


def validate_registration_username(username: str | None) -> tuple[str, str | None]:
    username = normalize_registration_username(username)
    if not username:
        return username, "missing_username"
    if sanitize_username(username) != username:
        return username, "invalid_username"
    if User.get(name=username) is not None:
        return username, "username_taken"
    if OldUsername.get(username) is not None:
        return username, "username_not_allowed"
    return username, None


def normalize_registration_email(email: str | None) -> str:
    return email.strip().lower() if email else ""


def validate_registration_email(email: str | None) -> tuple[str, str | None]:
    email = normalize_registration_email(email)
    if not email:
        return email, "missing_email"
    try:
        # anything that is not a well formed address has to be turned away here:
        # Deliverability is not checked, that would mean a DNS lookup on the request
        # path.
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        return email, "invalid_email"
    if DomainBlacklist.is_email_blacklisted(email):
        return email, "domain_blacklisted"
    if User.get(email=email) is not None:
        return email, "email_taken"
    return email, None
