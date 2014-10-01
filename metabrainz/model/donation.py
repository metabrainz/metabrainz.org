from metabrainz.model import db
from flask import current_app
from wepay import WePay
import re


class Donation(db.Model):
    __tablename__ = "donation"

    id = db.Column(db.Integer, primary_key=True)

    # Personal details
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    moderator = db.Column(db.String, server_default="")
    contact = db.Column(db.Boolean, server_default="FALSE")
    anonymous = db.Column("anon", db.Boolean, server_default="FALSE")
    address_street = db.Column(db.String, server_default="")
    address_city = db.Column(db.String, server_default="")
    address_state = db.Column(db.String, server_default="")
    address_postcode = db.Column(db.String, server_default="")
    address_country = db.Column(db.String, server_default="")

    # Transaction details
    timestamp = db.Column(db.DateTime, server_default="now()")
    paypal_trans_id = db.Column(db.String(32), nullable=False)
    amount = db.Column(db.Numeric(11, 2), nullable=False)
    fee = db.Column(db.String, server_default="")
    memo = db.Column(db.String, server_default="")

    def verify_and_log_wepay_checkout(self, checkout_id, editor, anonymous, can_contact):
        # Looking up updated information about the object
        wepay = WePay(production=current_app.config['PAYMENT_PRODUCTION'],
                      access_token=current_app.config['WEPAY_ACCESS_TOKEN'])

        details = wepay.call('/checkout', {'checkout_id': checkout_id})

        if 'error' in details:
            return False

        if 'payer_email' in details and self.is_donor_blocked(details['payer_email']):
            return True

        if details['state'] in ['settled', 'captured']:
            # Payment has been received
            # TODO: Create a record in the database.
            # TODO: Send receipt.
            pass

        elif details['state'] in ['authorized', 'reserved']:
            # Payment is pending
            pass

        elif details['state'] in ['expired', 'cancelled', 'failed', 'refunded', 'chargeback']:
            # Payment has failed
            pass

        else:
            # Unknown status
            return False

        return True

    @staticmethod
    def is_donor_blocked(email):
        pattern = re.compile('^yewm200')
        return email == 'gypsy313309496@aol.com' or pattern.match(email)
