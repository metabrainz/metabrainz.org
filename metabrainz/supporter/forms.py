from flask_babel import gettext
from wtforms import BooleanField, TextAreaField, ValidationError
from wtforms.fields import StringField, URLField, DecimalField
from wtforms.validators import DataRequired, Length

from metabrainz.index.forms import DatasetsField, MeBFlaskForm
from metabrainz.user.forms import UserSignupForm
from metabrainz.mtcaptcha import MTCaptchaField, validate_mtcaptcha


class SupporterFieldsMixin:
    """Mixin containing common supporter fields for both signup and upgrade forms."""
    contact_name = StringField(validators=[DataRequired(gettext("Contact name is required!"))])
    usage_desc = TextAreaField(
        gettext("Can you please tell us more about the project in which you'd like to use our data? Do you plan to self host the data or use our APIs?"),
        validators=[
            DataRequired(gettext("Please, tell us how you (will) use our data.")),
            Length(max=500, message=gettext("Please, limit usage description to 500 characters.")),
        ]
    )
    agreement = BooleanField(validators=[DataRequired(message=gettext("You need to accept the agreement!"))])
    mtcaptcha = MTCaptchaField(validators=[validate_mtcaptcha])


class CommercialFieldsMixin:
    """Mixin containing commercial supporter specific fields for both signup and upgrade forms."""
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

    def validate_amount_pledged(self, field):
        """Validate that amount pledged meets tier minimum and set default if empty."""
        if field.data is None:
            field.data = self.tier.price
        elif field.data < self.tier.price:
            raise ValidationError(gettext(
                "Custom amount must be more than threshold amount "
                "for selected tier or equal to it!"
            ))


class NonCommercialFieldsMixin:
    """Mixin containing non-commercial specific fields."""
    datasets = DatasetsField()


class SupporterSignUpForm(SupporterFieldsMixin, UserSignupForm):
    """Base sign up form for new supporters."""
    pass


class NonCommercialSignUpForm(NonCommercialFieldsMixin, SupporterSignUpForm):
    """Sign up form for non-commercial supporters."""

    def __init__(self, available_datasets, **kwargs):
        super().__init__(**kwargs)
        self.datasets.choices = available_datasets


class CommercialSignUpForm(CommercialFieldsMixin, SupporterSignUpForm):
    """Sign up form for commercial supporters."""

    def __init__(self, selected_tier, **kwargs):
        super().__init__(**kwargs)
        self.tier = selected_tier


# Upgrade forms (exclude user account fields, inherit from MeBFlaskForm)
class SupporterUpgradeForm(SupporterFieldsMixin, MeBFlaskForm):
    """Base upgrade form for existing users becoming supporters."""
    pass


class NonCommercialUpgradeForm(NonCommercialFieldsMixin, SupporterUpgradeForm):
    """Upgrade form for existing users becoming non-commercial supporters."""

    def __init__(self, available_datasets, **kwargs):
        super().__init__(**kwargs)
        self.datasets.choices = available_datasets


class CommercialUpgradeForm(CommercialFieldsMixin, SupporterUpgradeForm):
    """Upgrade form for existing users becoming commercial supporters."""

    def __init__(self, selected_tier, **kwargs):
        super().__init__(**kwargs)
        self.tier = selected_tier
