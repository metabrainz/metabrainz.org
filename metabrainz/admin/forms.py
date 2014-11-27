from flask_wtf import Form
from wtforms import StringField, BooleanField
from wtforms.fields.html5 import DateField, EmailField, DecimalField
from wtforms.validators import DataRequired


class AddDonationForm(Form):
    """Form for manually adding donations."""
    first_name = StringField("First name", validators=[DataRequired("First name is required.")])
    last_name = StringField("Last name", validators=[DataRequired("Last name is required.")])
    email = EmailField("Email", validators=[DataRequired("Email is required.")])

    can_contact = BooleanField("This donor may be contacted", default=True)
    anonymous = BooleanField("This donor wishes to remain anonymous")

    address_street = StringField("Street")
    address_city = StringField("City")
    address_state = StringField("State")
    address_postcode = StringField("Postcode")
    address_country = StringField("Country")

    payment_date = DateField("Payment date")
    amount = DecimalField("Amount (USD)", validators=[DataRequired("You need to specify amount.")])
    fee = DecimalField("Fee (USD)", default=0)

    editor = StringField("Editor name")

    memo = StringField("Memo")
