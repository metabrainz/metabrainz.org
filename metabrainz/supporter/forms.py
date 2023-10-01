from flask_wtf import FlaskForm, RecaptchaField
from flask_babel import gettext
from wtforms import BooleanField, TextAreaField, validators
from wtforms.fields import StringField, SelectMultipleField, EmailField, URLField, DecimalField
from wtforms.validators import DataRequired, Length
from wtforms.widgets import ListWidget, CheckboxInput

from metabrainz.user.forms import UserSignupForm


class DatasetsField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

    def __init__(self, **kwargs):
        super().__init__("Datasets", **kwargs, coerce=int)

    def iter_choices(self):
        for dataset in self.choices:
            selected = self.data is not None and dataset.id in self.data
            yield dataset.id, dataset.name, selected

    def pre_validate(self, form):
        if self.data:
            values = list(c.id for c in self.choices)
            for d in self.data:
                if d not in values:
                    raise ValueError(self.gettext("'%(value)s' is not a valid choice for this field") % dict(value=d))

    def post_validate(self, form, validation_stopped):
        if validation_stopped:
            return
        datasets_dict = {self.coerce(dataset.id): dataset for dataset in self.choices}
        self.data = [datasets_dict.get(x) for x in self.data]


class SupporterSignUpForm(UserSignupForm):
    """Base sign up form for new supporters.

    Contains common fields required from both commercial and non-commercial
    supporters.
    """
    contact_name = StringField(validators=[DataRequired(gettext("Contact name is required!"))])
    contact_email = EmailField(validators=[DataRequired(gettext("Email address is required!"))])
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


class SupporterEditForm(FlaskForm):
    """Supporter profile editing form."""
    contact_name = StringField(gettext("Name"), [
        validators.DataRequired(message=gettext("Contact name field is empty.")),
    ])
    contact_email = EmailField(gettext("Email"), [
        validators.Optional(strip_whitespace=False),
        validators.Email(message=gettext("Email field is not a valid email address.")),
        validators.DataRequired(message=gettext("Contact email field is empty.")),
    ])


class NonCommercialSupporterEditForm(SupporterEditForm):
    datasets = DatasetsField()

    def __init__(self, available_datasets, **kwargs):
        super().__init__(**kwargs)
        self.datasets.choices = available_datasets
        self.descriptions = {d.id: d.description for d in available_datasets}


class CommercialSupporterEditForm(SupporterEditForm):
    pass