from flask_wtf import Form
from wtforms import DecimalField, StringField, BooleanField
from wtforms.widgets import HiddenInput
from wtforms.validators import DataRequired
from flask import url_for, request


class WePayForm(Form):
    """Form for WePay donations."""
    amount = DecimalField(
        "Amount",
        validators=[DataRequired("You need to specify amount of money that you want to donate.")])
    editor = StringField("User name")
    can_contact = BooleanField("You may email me about future fundraising events (this will be very seldom)")
    anonymous = BooleanField("I would like this donation to be anonymous (don't list my name on the finances page)")

    def __init__(self, amount=None, **kwargs):
        kwargs.setdefault("amount", amount)
        Form.__init__(self, **kwargs)


    """Base form for PayPal donations."""
class BasePayPalForm(Form):
    business = StringField(widget=HiddenInput(), default="donations@metabrainz.org")
    no_shipping = StringField(widget=HiddenInput(), default="2")
    ret_url = StringField(widget=HiddenInput(), id="return", default=url_for('donation.complete', _external=True))
    cancel_return = StringField(widget=HiddenInput(), default=url_for('donation.cancelled', _external=True))
    currency_code = StringField(widget=HiddenInput(), default="USD")
    amount = DecimalField("Amount")

    # Setting callback_uri that will receive IPNs if endpoint is not local
    if not (request.headers['Host'].startswith('localhost') or request.headers['Host'].startswith('127.0.0.1')):
        notify_url = StringField(widget=HiddenInput(), default=url_for('donation.paypal_ipn', _external=True))

    # Passthrough variables:
    editor = StringField("User name", id="item_number_0")
    can_contact = BooleanField("You may email me about future fundraising events (this will be very seldom)", id="item_number_1")
    anonymous = BooleanField("I would like this donation to be anonymous (don't list my name on the finances page)", id="item_number_2")

    def __init__(self, amount=None, **kwargs):
        kwargs.setdefault("amount", amount)
        Form.__init__(self, **kwargs)


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
