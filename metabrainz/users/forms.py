from flask_wtf import Form, RecaptchaField
from wtforms import StringField, BooleanField, TextAreaField, RadioField, validators
from wtforms.fields.html5 import EmailField, URLField, DecimalField
from wtforms.validators import DataRequired, Length

PAYMENT_METHOD_PAYPAL = 'paypal'
PAYMENT_METHOD_STRIPE = 'stripe'
PAYMENT_METHOD_INVOICING = 'invoicing'
PAYMENT_METHOD_BITCOIN = 'bitcoin'


class UserSignUpForm(Form):
    """Base sign up form for new users.

    Contains common fields required from both commercial and non-commercial
    users.
    """
    contact_name = StringField(validators=[DataRequired("Contact name is required!")])
    contact_email = EmailField(validators=[DataRequired("Email address is required!")])
    usage_desc = TextAreaField("How are you using our data?", validators=[
        DataRequired("Please, tell us how you (will) use our data."),
        Length(max=150, message="Please, limit usage description to 150 characters."),
    ])
    agreement = BooleanField(validators=[DataRequired(message="You need to accept the agreement!")])
    recaptcha = RecaptchaField()

    def __init__(self, default_email=None, **kwargs):
        kwargs.setdefault('contact_email', default_email)
        Form.__init__(self, **kwargs)


class NonCommercialSignUpForm(UserSignUpForm):
    """Sign up form for non-commercial users."""
    pass


class CommercialSignUpForm(UserSignUpForm):
    """Sign up form for commercial users."""
    org_name = StringField("Organization name", validators=[
        DataRequired("You need to specify the name of your organization.")
    ])
    org_desc = TextAreaField("Organization description", validators=[
        DataRequired("You need to provide description of your organization."),
    ])

    website_url = URLField("Website URL", validators=[
        DataRequired("You need to specify website of the organization."),
    ])
    logo_url = URLField("Logo image URL")
    api_url = URLField("API URL")

    address_street = StringField("Street")
    address_city = StringField("City")
    address_state = StringField("State / Province")
    address_postcode = StringField("Postcode")
    address_country = StringField("Country", validators=[
        DataRequired("You need to specify country.")
    ])

    payment_method = RadioField(
        "Choose a payment method:",
        choices=[
            (PAYMENT_METHOD_PAYPAL, "PayPal"),
            (PAYMENT_METHOD_STRIPE, "Stripe"),
            (PAYMENT_METHOD_INVOICING, "Invoicing"),
            (PAYMENT_METHOD_BITCOIN, "Bitcoin"),
        ],
        validators=[DataRequired(message="You need to choose a payment method!")],
    )
    amount_pledged = DecimalField()


class UserEditForm(Form):
    """User profile editing form."""
    contact_name = StringField("Name", [
        validators.DataRequired(message="Contact name field is empty."),
    ])
    contact_email = EmailField("Email", [
        validators.Optional(strip_whitespace=False),
        validators.Email(message="Email field is not a valid email address."),
        validators.DataRequired(message="Contact email field is empty."),
    ])
