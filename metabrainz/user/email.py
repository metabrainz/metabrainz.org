import hashlib
from datetime import datetime, timezone

from flask import url_for, request, render_template, current_app

from brainzutils.mail import send_mail
from metabrainz.model.user import User

VERIFY_EMAIL = "verify-email"
RESET_PASSWORD = "reset-password"
SET_PASSWORD = "set-password"


def create_email_link_checksum(purpose: str, user_id: int, email: str, timestamp: int) -> str:
    """ Create a checksum based on user details, time and a secret key for the user's email verification """
    text = f"{purpose}; user_id: {user_id}; email: {email}; timestamp: {timestamp}; secret: {current_app.config['EMAIL_VERIFICATION_SECRET_KEY']}"
    m = hashlib.sha256()
    m.update(text.encode("utf-8"))
    return m.hexdigest()


def _send_user_email(username: str, email: str, subject: str, content: str):
    if not current_app.config["DEBUG"]:
        send_mail(subject=subject, text=content, recipients=[f"{username} <{email}>"])


def send_verification_email(user: User, subject, template, **template_context):
    """ Send email for verification of user's email address. """
    timestamp = int(datetime.now().timestamp())
    email = user.unconfirmed_email

    checksum = create_email_link_checksum(VERIFY_EMAIL, user.id, email, timestamp)
    verification_link = url_for(
        "users.verify_email",
        user_id=user.id,
        timestamp=timestamp,
        checksum=checksum,
        _external=True
    )
    content = render_template(
        template,
        username=user.name,
        verification_link=verification_link,
        ip=request.remote_addr,
        **template_context,
    )
    _send_user_email(user.name, email, subject, content)


def send_forgot_username_email(user: User):
    """ Send email for forgotten username. """
    content = render_template(
        "email/user-forgot-username.txt",
        username=user.name,
        forgot_password_link=url_for("users.lost_password")
    )
    _send_user_email(user.name, user.email, "Lost username", content)


def send_forgot_password_email(user: User):
    """ Send email for resetting the user's password. """
    timestamp = int(datetime.now().timestamp())
    checksum = create_email_link_checksum(RESET_PASSWORD, user.id, user.get_email_any(), timestamp)
    reset_password_link = url_for("users.reset_password", user_id=user.id, timestamp=timestamp, checksum=checksum, _external=True)
    content = render_template(
        "email/user-password-reset.txt",
        reset_password_link=reset_password_link,
        contact_url="https://metabrainz.org/contact"
    )
    _send_user_email(user.name, user.get_email_any(), "Password reset request", content)


def send_welcome_email(
    user: User,
    oauth_client_name: str,
    oauth_client_description: str,
    granted_scopes: list[dict[str, str]],
):
    """Send a newly provisioned user a link for choosing their password."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    email = user.get_email_any()
    checksum = create_email_link_checksum(SET_PASSWORD, user.id, email, timestamp)
    password_link = url_for(
        "users.reset_password",
        user_id=user.id,
        timestamp=timestamp,
        checksum=checksum,
        initial_setup="1",
        _external=True,
    )
    content = render_template(
        "email/user-welcome.txt",
        username=user.name,
        oauth_client_name=oauth_client_name,
        oauth_client_description=oauth_client_description,
        granted_scopes=granted_scopes,
        password_link=password_link,
        contact_url="https://metabrainz.org/contact",
    )
    _send_user_email(user.name, email, "Welcome to MetaBrainz", content)
