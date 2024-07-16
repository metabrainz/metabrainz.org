from flask_wtf import FlaskForm
from flask_babel import lazy_gettext
from wtforms import StringField, BooleanField
from wtforms.fields import RadioField, DecimalField, IntegerField
from wtforms.fields.simple import HiddenField
from wtforms.validators import DataRequired
from metabrainz.payments import Currency


class BasePaymentForm(FlaskForm):
    amount = DecimalField(validators=[DataRequired(lazy_gettext("You need to specify amount!"))])
    currency = RadioField(
        choices=[
            (Currency.US_Dollar.value, lazy_gettext("USD")),
            (Currency.Euro.value, lazy_gettext("EUR")),
        ],
        default=Currency.US_Dollar.value,
        validators=[DataRequired(lazy_gettext("You need to specify currency!"))],
    )
    recurring = BooleanField()


class DonationForm(BasePaymentForm):
    editor = StringField()  # MusicBrainz username
    can_contact = BooleanField()
    anonymous = BooleanField()


class PaymentForm(BasePaymentForm):
    """Payment form for organizations."""
    currency = HiddenField()
    invoice_number = IntegerField(validators=[DataRequired(lazy_gettext("You need to specify invoice number!"))])
