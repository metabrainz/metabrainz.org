from gettext import gettext

from flask_wtf import FlaskForm
from wtforms import validators
from wtforms.fields import SelectMultipleField, EmailField, StringField
from wtforms.validators import DataRequired
from wtforms.widgets.core import ListWidget, CheckboxInput


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

    @property
    def props_errors(self):
        return {k: ". ".join(v) for k, v in self.errors.items()}


class DatasetsField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

    def __init__(self, **kwargs):
        super().__init__("Datasets", **kwargs, coerce=int)

    def iter_choices(self):
        for dataset in self.choices:
            selected = self.data is not None and dataset["id"] in self.data
            yield dataset["id"], dataset["name"], selected

    def pre_validate(self, form):
        if self.data:
            values = list(c["id"] for c in self.choices)
            for d in self.data:
                if d not in values:
                    raise ValueError(self.gettext("'%(value)s' is not a valid choice for this field") % dict(value=d))

    def post_validate(self, form, validation_stopped):
        if validation_stopped:
            return
        datasets_dict = {self.coerce(dataset["id"]): dataset for dataset in self.choices}
        self.data = [datasets_dict.get(x) for x in self.data]


class UserEditForm(MeBFlaskForm):
    """ Login form for existing users. """
    email = EmailField(validators=[DataRequired(gettext("Email address is required!"))])


class SupporterEditForm(UserEditForm):
    """Supporter profile editing form."""
    contact_name = StringField(gettext("Name"), [
        validators.DataRequired(message=gettext("Contact name field is empty.")),
    ])

class NonCommercialSupporterEditForm(SupporterEditForm):
    datasets = DatasetsField()

    def __init__(self, available_datasets, **kwargs):
        super().__init__(**kwargs)
        self.datasets.choices = available_datasets
        self.descriptions = {d.id: d.description for d in available_datasets}


class CommercialSupporterEditForm(SupporterEditForm):
    pass
