import hashlib
from datetime import datetime

from flask import url_for, request, render_template, current_app

from brainzutils.mail import send_mail
from metabrainz.model.user import User

VERIFY_EMAIL = "verify-email"
RESET_PASSWORD = "reset-password"


def create_email_link_checksum(purpose: str, user: User, timestamp: int) -> str:
    """ Create a checksum based on user details, time and a secret key for the user's email verification """
    text = f"{purpose}; user_id: {user.id}; email: {user.email}; timestamp: {timestamp}; secret: {current_app.config['EMAIL_VERIFICATION_SECRET_KEY']}"
    m = hashlib.sha256()
    m.update(text.encode("utf-8"))
    return m.hexdigest()


def _send_user_email(user: User, subject: str, content: str):
    send_mail(subject=subject, text=content, recipients=[f"{user.name} <{user.email}>"])


def send_verification_email(user: User):
    """ Send email for verification of user's email address. """
    timestamp = int(datetime.now().timestamp())
    checksum = create_email_link_checksum(VERIFY_EMAIL, user, timestamp)
    verification_link = url_for("users.verify_email", user_id=user.id, timestamp=timestamp, checksum=checksum)
    content = render_template(
        "email/user-email-address-verification.txt",
        username=user.name,
        verification_link=verification_link,
        ip=request.remote_addr
    )
    _send_user_email(user, "Please verify your email address", content)


def send_forgot_username_email(user: User):
    """ Send email for forgotten username. """
    timestamp = int(datetime.now().timestamp())
    content = render_template(
        "email/user-forgot-username.txt",
        username=user.name,
        forgot_password_link=url_for("users.lost_password")
    )
    _send_user_email(user, "Lost username", content)


def send_forgot_password_email(user: User):
    """ Send email for resetting the user's password. """
    timestamp = int(datetime.now().timestamp())
    checksum = create_email_link_checksum(RESET_PASSWORD, user, timestamp)
    reset_password_link = url_for("users.reset_password", user_id=user.id, timestamp=timestamp, checksum=checksum, _external=True)
    content = render_template(
        "email/user-password-reset.txt",
        reset_password_link=reset_password_link,
        contact_url="https://metabrainz.org/contact"
    )
    _send_user_email(user, "Password reset request", content)
