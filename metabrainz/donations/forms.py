from flask_wtf import Form
from wtforms import StringField, BooleanField
from wtforms.fields.html5 import DecimalField
from wtforms.validators import DataRequired


class DonationForm(Form):
    amount = DecimalField(validators=[DataRequired("You need to specify amount of money that you want to donate.")])
    editor = StringField()  # MusicBrainz username
    recurring = BooleanField()
    can_contact = BooleanField()
    anonymous = BooleanField()
