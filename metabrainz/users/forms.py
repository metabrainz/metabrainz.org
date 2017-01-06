from flask_wtf import Form, RecaptchaField
from flask_babel import gettext
from wtforms import StringField, BooleanField, TextAreaField, RadioField, validators
from wtforms.fields.html5 import EmailField, URLField, DecimalField
from wtforms.validators import DataRequired, Length


class UserSignUpForm(Form):
    """Base sign up form for new users.

    Contains common fields required from both commercial and non-commercial
    users.
    """
    contact_name = StringField(validators=[DataRequired(gettext("Contact name is required!"))])
    contact_email = EmailField(validators=[DataRequired(gettext("Email address is required!"))])
    usage_desc = TextAreaField(gettext("How are you using our data?"), validators=[
        DataRequired(gettext("Please, tell us how you (will) use our data.")),
        Length(max=150, message=gettext("Please, limit usage description to 150 characters.")),
    ])
    agreement = BooleanField(validators=[DataRequired(message=gettext("You need to accept the agreement!"))])
    recaptcha = RecaptchaField()

    def __init__(self, default_email=None, **kwargs):
        kwargs.setdefault('contact_email', default_email)
        Form.__init__(self, **kwargs)


class NonCommercialSignUpForm(UserSignUpForm):
    """Sign up form for non-commercial users."""
    pass


class CommercialSignUpForm(UserSignUpForm):
    """Sign up form for commercial users."""
    org_name = StringField(gettext("Organization name"), validators=[
        DataRequired(gettext("You need to specify the name of your organization."))
    ])
    org_desc = TextAreaField(gettext("Organization description"), validators=[
        DataRequired(gettext("You need to provide description of your organization.")),
    ])

    website_url = URLField(gettext("Website URL"), validators=[
        DataRequired(gettext("You need to specify website of the organization.")),
    ])
    logo_url = URLField(gettext("Logo image URL"))
    api_url = URLField(gettext("API URL"))

    address_street = StringField(gettext("Street"), validators=[
        DataRequired(gettext("You need to specify street."))
    ])
    address_city = StringField(gettext("City"), validators=[
        DataRequired(gettext("You need to specify city."))
    ])
    address_state = StringField(gettext("State / Province"), validators=[
        DataRequired(gettext("You need to specify state/province."))
    ])
    address_postcode = StringField(gettext("Postcode"), validators=[
        DataRequired(gettext("You need to specify postcode."))
    ])
    address_country = StringField(gettext("Country"), validators=[
        DataRequired(gettext("You need to specify country."))
    ])

    amount_pledged = DecimalField()


class UserEditForm(Form):
    """User profile editing form."""
    contact_name = StringField(gettext("Name"), [
        validators.DataRequired(message=gettext("Contact name field is empty.")),
    ])
    contact_email = EmailField(gettext("Email"), [
        validators.Optional(strip_whitespace=False),
        validators.Email(message=gettext("Email field is not a valid email address.")),
        validators.DataRequired(message=gettext("Contact email field is empty.")),
    ])
