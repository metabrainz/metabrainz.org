from flask_wtf import Form
from wtforms import DecimalField, StringField, BooleanField
from wtforms.validators import DataRequired


class WePayForm(Form):
    amount = DecimalField(
        "Amount",
        validators=[DataRequired("You need to specify amount of money that you want to donate.")])
    editor = StringField("User name")
    can_contact = BooleanField("You may email me about future fundraising events (this will be very seldom)")
    anonymous = BooleanField("I would like this donation to be anonymous (don't list my name on the finances page)")

    def __init__(self, amount=None, **kwargs):
        kwargs.setdefault("amount", amount)
        Form.__init__(self, **kwargs)
