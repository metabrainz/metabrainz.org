from flask_babel import gettext
from wtforms import BooleanField, PasswordField, ValidationError
from wtforms.fields import StringField, EmailField
from wtforms.validators import DataRequired, EqualTo, Length

from metabrainz.model.domain_blacklist import DomainBlacklist
from metabrainz.index.forms import MeBFlaskForm
from metabrainz.mtcaptcha import MTCaptchaField, validate_mtcaptcha


def validate_email_domain(form, field):
    """Validator to check if email domain is blacklisted."""
    if field.data and DomainBlacklist.is_email_blacklisted(field.data):
        raise ValidationError(gettext("Registration from this email domain is not allowed."))


class UserSignupForm(MeBFlaskForm):
    """ Sign up form for new users. """
    username = StringField(gettext("Username"), validators=[DataRequired(gettext("Username is required!"))])
    email = EmailField(validators=[
        DataRequired(gettext("Email address is required!")),
        validate_email_domain
    ])
    password = PasswordField(validators=[
        DataRequired(gettext("Password is required!")),
        Length(min=8, max=64)
    ])
    confirm_password = PasswordField(validators=[
        DataRequired(gettext("Confirm Password is required!")),
        Length(min=8, max=64),
        EqualTo("password", gettext("Confirm Password should match password!"))
    ])
    mtcaptcha = MTCaptchaField("MTCaptcha", validators=[validate_mtcaptcha])


class UserLoginForm(MeBFlaskForm):
    """ Login form for existing users. """
    username = StringField(gettext("Username"), validators=[DataRequired(gettext("Username is required!"))])
    password = PasswordField(gettext("Password"), validators=[DataRequired(gettext("Password is required!"))])
    remember_me = BooleanField(gettext("Remember me"), default="checked")


class ForgotUsernameForm(MeBFlaskForm):
    """ Form to request lost username email. """
    email = EmailField(validators=[DataRequired(gettext("Email address is required!"))])


class ForgotPasswordForm(MeBFlaskForm):
    """ Form to request reset password link. """
    username = StringField(gettext("Username"), validators=[DataRequired(gettext("Username is required!"))])
    email = EmailField(validators=[DataRequired(gettext("Email address is required!"))])


class ResetPasswordForm(MeBFlaskForm):
    """ Form for a user to reset their password. """
    password = PasswordField(validators=[
        DataRequired(gettext("Password is required!")),
        Length(min=8, max=64)
    ])
    confirm_password = PasswordField(validators=[
        DataRequired(gettext("Confirm Password is required!")),
        Length(min=8, max=64),
        EqualTo("password", gettext("Confirm Password should match password!"))
    ])
