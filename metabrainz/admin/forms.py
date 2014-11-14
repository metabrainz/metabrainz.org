from flask_wtf import Form
from wtforms import DecimalField, StringField, BooleanField
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired


class AddDonationForm(Form):
    """Form for manually adding donations."""
    first_name = StringField("First name", validators=[DataRequired()])
    last_name = StringField("Last name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])

    can_contact = BooleanField("This donor may be contacted")
    anonymous = BooleanField("This donor wishes to remain anonymous")

    address_street = StringField("Street")
    address_city = StringField("City")
    address_state = StringField("State")
    address_postcode = StringField("Postcode")
    address_country = StringField("Country")

    payment_date = DateField("Payment date")
    amount = DecimalField("Amount", validators=[DataRequired()])
    fee = DecimalField("Fee", validators=[DataRequired()])

    editor = StringField("Editor name")

    memo = StringField("Memo")
