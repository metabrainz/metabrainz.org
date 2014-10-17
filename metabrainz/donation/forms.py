from flask_wtf import Form
from wtforms import DecimalField, StringField, BooleanField
from wtforms.widgets import HiddenInput
from wtforms.validators import DataRequired
from flask import url_for


class BaseDonationForm(Form):
    """Base form for donations."""
    amount = DecimalField(
        "Amount",
        validators=[DataRequired("You need to specify amount of money that you want to donate.")])
    editor = StringField("User name")
    can_contact = BooleanField("You may email me about future fundraising events (this will be very seldom)")
    anonymous = BooleanField("I would like this donation to be anonymous (don't list my name on the finances page)")

    def __init__(self, amount=None, **kwargs):
        kwargs.setdefault("amount", amount)
        Form.__init__(self, **kwargs)


class BasePayPalForm(BaseDonationForm):
    """Base form for PayPal donations."""
    business = StringField(widget=HiddenInput(), default="donations@metabrainz.org")
    no_shipping = StringField(widget=HiddenInput(), default="2")
    ret_url = StringField(widget=HiddenInput(), id="return", default=url_for('donation.complete', _external=True))
    cancel_return = StringField(widget=HiddenInput(), default=url_for('donation.cancelled', _external=True))
    currency_code = StringField(widget=HiddenInput(), default="USD")


class PayPalOneTimeForm(BasePayPalForm):
    """Form for one-time donations via PayPal."""
    cmd = StringField(widget=HiddenInput(), default="_xclick")
    item_name = StringField(widget=HiddenInput(), default="Donation to MetaBrainz Foundation")


class PayPalRecurringForm(BasePayPalForm):
    """Form for recurring donations via PayPal."""
    cmd = StringField(widget=HiddenInput(), default="_xclick-subscriptions")
    item_name = StringField(widget=HiddenInput(), default="Recurring donation to MetaBrainz Foundation")
    t3 = StringField(widget=HiddenInput(), default="M")
    p3 = StringField(widget=HiddenInput(), default="1")
    src = StringField(widget=HiddenInput(), default="1")
    sra = StringField(widget=HiddenInput(), default="1")
