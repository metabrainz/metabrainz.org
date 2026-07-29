from flask_babel import gettext
from wtforms import ValidationError


BCRYPT_MAX_PASSWORD_BYTES = 72


def validate_bcrypt_password_length(form, field):
    """Ensure bcrypt can hash or check the submitted password."""
    if field.data and len(field.data.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValidationError(
            gettext("Password must not exceed %(max_bytes)s bytes.", max_bytes=BCRYPT_MAX_PASSWORD_BYTES)
        )
