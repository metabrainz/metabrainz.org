from flask_wtf import Form
from flask_babel import gettext
from wtforms import StringField, BooleanField
from wtforms.fields.html5 import DecimalField, IntegerField
from wtforms.validators import DataRequired


class BasePaymentForm(Form):
    amount = DecimalField(validators=[DataRequired(gettext("You need to specify amount!"))])
    recurring = BooleanField()


class DonationForm(BasePaymentForm):
    editor = StringField()  # MusicBrainz username
    can_contact = BooleanField()
    anonymous = BooleanField()


class PaymentForm(BasePaymentForm):
    """Payment form for organizations."""
    invoice_number = IntegerField(validators=[DataRequired(gettext("You need to specify invoice number!"))])
