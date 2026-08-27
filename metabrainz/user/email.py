import hashlib
from datetime import datetime

from flask import url_for, request, render_template, current_app

from metabrainz.mail import send_mail
from metabrainz.model.user import User

VERIFY_EMAIL = "verify-email"
RESET_PASSWORD = "reset-password"

# The timestamp travels as "ts": "&times" is an HTML entity for × that parsers decode even
# without the trailing semicolon, so mail clients turned "&timestamp=" into "×tamp=".


def create_email_link_checksum(purpose: str, user_id: int, email: str, timestamp: int, binding: str = None) -> str:
    """ Create a checksum based on user details, time and a secret key for the user's email verification

    ``binding`` ties the link to account state that changes, invalidating it when that does.
    """
    text = f"{purpose}; user_id: {user_id}; email: {email}; timestamp: {timestamp}; secret: {current_app.config['EMAIL_VERIFICATION_SECRET_KEY']}"
    if binding is not None:
        text = f"{text}; binding: {binding}"
    m = hashlib.sha256()
    m.update(text.encode("utf-8"))
    return m.hexdigest()


def create_reset_password_checksum(user: User, timestamp: int) -> str:
    """ Create the checksum for a user's password reset link.

    Binding it to the password hash makes the link single use: changing the password
    invalidates every reset link outstanding for the user, including the one just used.
    """
    return create_email_link_checksum(
        RESET_PASSWORD, user.id, user.get_email_any(), timestamp, binding=user.password
    )


def _send_user_email(email: str, subject: str, content: str):
    if not current_app.config["DEBUG"]:
        if not email:
            raise ValueError("Cannot send user email without a recipient address")
        send_mail(subject=subject, text=content, recipients=[email])


def send_verification_email(user: User, subject, template):
    """ Send email for verification of user's email address. """
    timestamp = int(datetime.now().timestamp())
    email = user.unconfirmed_email

    checksum = create_email_link_checksum(VERIFY_EMAIL, user.id, email, timestamp)
    verification_link = url_for(
        "users.verify_email",
        user_id=user.id,
        ts=timestamp,
        checksum=checksum,
        _external=True
    )
    content = render_template(
        template,
        username=user.name,
        verification_link=verification_link,
        ip=request.remote_addr
    )
    _send_user_email(email, subject, content)


def send_forgot_username_email(user: User):
    """ Send email for forgotten username. """
    content = render_template(
        "email/user-forgot-username.txt",
        username=user.name,
        forgot_password_link=url_for("users.lost_password")
    )
    _send_user_email(user.get_email_any(), "Lost username", content)


def send_forgot_password_email(user: User):
    """ Send email for resetting the user's password. """
    timestamp = int(datetime.now().timestamp())
    checksum = create_reset_password_checksum(user, timestamp)
    reset_password_link = url_for("users.reset_password", user_id=user.id, ts=timestamp, checksum=checksum, _external=True)
    content = render_template(
        "email/user-password-reset.txt",
        reset_password_link=reset_password_link,
        contact_url="https://metabrainz.org/contact"
    )
    _send_user_email(user.get_email_any(), "Password reset request", content)
