"""MTCaptcha integration for Flask-WTF forms."""
import requests

from flask import current_app
from wtforms import StringField
from wtforms.validators import ValidationError


class MTCaptchaField(StringField):
    """MTCaptcha field for WTForms."""

    def __init__(self, label="", validators=None, **kwargs):
        validators = validators or []
        super().__init__(label, validators, **kwargs)

    def _value(self):
        if self.data:
            return self.data
        return ""


def validate_mtcaptcha(form, field):
    """Validate MTCaptcha response token.

    This validator checks if the MTCaptcha token is valid by making a request
    to the MTCaptcha verification API.

    Args:
        form: The form instance containing the field
        field: The field to validate

    Raises:
        ValidationError: If the MTCaptcha validation fails
    """
    # skip capcha validation during tests
    if current_app.config["TESTING"]:
        return

    if not field.data:
        raise ValidationError("Please complete the captcha challenge.")

    mtcaptcha_private_key = current_app.config.get("MTCAPTCHA_PRIVATE_KEY")

    if not mtcaptcha_private_key:
        current_app.logger.error("MTCAPTCHA_PRIVATE_KEY not configured")
        raise ValidationError("Captcha configuration error.")

    verify_url = "https://service.mtcaptcha.com/mtcv1/api/checktoken"

    payload = {
        "privatekey": mtcaptcha_private_key,
        "token": field.data,
    }

    try:
        response = requests.get(verify_url, params=payload, timeout=10)
        response.raise_for_status()
        result = response.json()

        if not result.get("success"):
            current_app.logger.warning(
                f"MTCaptcha validation failed: {result.get('fail-codes', [])}"
            )
            raise ValidationError("Captcha validation failed. Please try again.")

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"MTCaptcha API request failed: {e}")
        raise ValidationError("Captcha verification error. Please try again.")
