from flask_babel import gettext
from flask_wtf import FlaskForm, RecaptchaField
from wtforms import BooleanField, PasswordField
from wtforms.fields.core import StringField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, EqualTo, Length


class MeBFlaskForm(FlaskForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_errors = []

    @property
    def errors(self):
        errors = super().errors
        if self.form_errors:
            errors[None] = self.form_errors
        return errors


class UserSignupForm(MeBFlaskForm):
    """ Sign up form for new users. """
    username = StringField(gettext("Username"), validators=[DataRequired(gettext("Username is required!"))])
    email = EmailField(validators=[DataRequired(gettext("Email address is required!"))])
    password = PasswordField(validators=[
        DataRequired(gettext("Password is required!")),
        Length(min=8, max=64)
    ])
    confirm_password = PasswordField(validators=[
        DataRequired(gettext("Confirm Password is required!")),
        Length(min=8, max=64),
        EqualTo("password", gettext("Confirm Password should match password!"))
    ])
    recaptcha = RecaptchaField("Recaptcha")


# TODO: Consider adding recaptcha fields to remaining forms


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


class UserEditForm(MeBFlaskForm):
    """ Login form for existing users. """
    email = EmailField(validators=[DataRequired(gettext("Email address is required!"))])
