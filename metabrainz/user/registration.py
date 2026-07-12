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
    if OldUsername.query.filter_by(username=username).first() is not None:
        return username, "username_not_allowed"
    return username, None


def normalize_registration_email(email: str | None) -> str:
    return email.strip().lower() if email else ""


def validate_registration_email(email: str | None) -> tuple[str, str | None]:
    email = normalize_registration_email(email)
    if not email:
        return email, "missing_email"
    if "@" not in email:
        return email, "invalid_email"
    if DomainBlacklist.is_email_blacklisted(email):
        return email, "domain_blacklisted"
    if User.get(email=email) is not None:
        return email, "email_taken"
    return email, None
