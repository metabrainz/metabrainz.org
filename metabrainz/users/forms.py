from flask_wtf import Form, RecaptchaField
from wtforms import StringField, TextAreaField, RadioField
from wtforms.fields.html5 import EmailField, URLField
from wtforms.validators import DataRequired


class UserSignUpForm(Form):
    """Base sign up form for new users.

    Contains common fields required from both commercial and non-commercial
    users.
    """
    contact_name = StringField(validators=[DataRequired("Contact name is required!")])
    contact_email = EmailField(validators=[DataRequired("Email address is required!")])
    description = TextAreaField("How are you using our data?",
                                validators=[DataRequired("Please, tell us how you (will) use our data.")])
    # TODO: Add agreement field.
    recaptcha = RecaptchaField()

    def __init__(self, default_email=None, **kwargs):
        kwargs.setdefault('contact_email', default_email)
        Form.__init__(self, **kwargs)


class CommercialSignUpForm(UserSignUpForm):
    """Sign up form specifically for commercial users."""
    org_name = StringField("Organization name", validators=[DataRequired("You need to specify the name of your organization.")])

    website_url = URLField("Website URL", validators=[DataRequired("You need to specify website of the organization.")])
    logo_url = URLField("Logo image URL")
    api_url = URLField("API URL")

    address_street = StringField("Street")
    address_city = StringField("City")
    address_state = StringField("State")
    address_postcode = StringField("Postcode")
    address_country = StringField("Country")

    payment_method = RadioField(
        "Choose a payment method:",
        choices=[
            ("paypal", "PayPal"),
            ("stripe", "Stripe"),
            ("invoicing", "Invoicing"),
            ("bitcoin", "Bitcoin"),
        ],
        validators=[DataRequired(message="You need to choose a payment method!")])
