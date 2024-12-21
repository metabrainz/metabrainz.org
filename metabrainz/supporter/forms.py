from flask_wtf import FlaskForm, RecaptchaField
from flask_babel import gettext
from wtforms import BooleanField, TextAreaField, validators
from wtforms.fields import StringField, EmailField, URLField, DecimalField
from wtforms.validators import DataRequired, Length

from metabrainz.index.forms import DatasetsField
from metabrainz.user.forms import UserSignupForm


class SupporterSignUpForm(UserSignupForm):
    """Base sign up form for new supporters.

    Contains common fields required from both commercial and non-commercial
    supporters.
    """
    contact_name = StringField(validators=[DataRequired(gettext("Contact name is required!"))])
    usage_desc = TextAreaField(
        gettext("Can you please tell us more about the project in which you'd like to use our data? Do you plan to self host the data or use our APIs?"),
        validators=[
            DataRequired(gettext("Please, tell us how you (will) use our data.")),
            Length(max=500, message=gettext("Please, limit usage description to 500 characters.")),
        ]
    )
    agreement = BooleanField(validators=[DataRequired(message=gettext("You need to accept the agreement!"))])
    recaptcha = RecaptchaField()


class NonCommercialSignUpForm(SupporterSignUpForm):
    """Sign up form for non-commercial supporters."""
    datasets = DatasetsField()

    def __init__(self, available_datasets, **kwargs):
        super().__init__(**kwargs)
        self.datasets.choices = available_datasets
        self.descriptions = {d.id: d.description for d in available_datasets}


class CommercialSignUpForm(SupporterSignUpForm):
    """Sign up form for commercial supporters."""
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
