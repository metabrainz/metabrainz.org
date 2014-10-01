from metabrainz.model import db
from flask import current_app
from wepay import WePay
import re


class Donation(db.Model):
    __tablename__ = 'donation'

    id = db.Column(db.Integer, primary_key=True)

    # Personal details
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    moderator = db.Column(db.String, server_default='')
    contact = db.Column('contact', db.Boolean, server_default='FALSE')
    anonymous = db.Column('anon', db.Boolean, server_default='FALSE')
    address_street = db.Column(db.String, server_default='')
    address_city = db.Column(db.String, server_default='')
    address_state = db.Column(db.String, server_default='')
    address_postcode = db.Column(db.String, server_default='')
    address_country = db.Column(db.String, server_default='')

    # Transaction details
    timestamp = db.Column(db.DateTime, server_default='now()')
    paypal_trans_id = db.Column(db.String(32), nullable=False)
    amount = db.Column(db.Numeric(11, 2), nullable=False)
    fee = db.Column(db.String, server_default='')
    memo = db.Column(db.String, server_default='')

    @classmethod
    def verify_and_log_wepay_checkout(cls, checkout_id, editor, anonymous, can_contact):
        # Looking up updated information about the object
        wepay = WePay(production=current_app.config['PAYMENT_PRODUCTION'],
                      access_token=current_app.config['WEPAY_ACCESS_TOKEN'])

        details = wepay.call('/checkout', {'checkout_id': checkout_id})

        if 'error' in details:
            return False

        if 'payer_email' in details and cls.is_donor_blocked(details['payer_email']):
            return True

        if details['gross'] < 0.50:
            # Tiny donation
            pass

        if details['state'] in ['settled', 'captured']:
            # Payment has been received

            new_donation = cls(
                first_name=details['payer_name'],
                last_name='',
                email=details['payer_email'],
                moderator=editor,
                can_contact=can_contact,
                anonymous=anonymous,
                amount=details['gross']-details['fee'],
                fee=details['fee'],
            )

            if 'shipping_address' in details:
                address = details['shipping_address']
                new_donation.address_street = "%s\n%s" % (address['address1'], address['address2'])
                new_donation.address_city = address['city']
                if 'state' in address:  # US address
                    new_donation.address_state = address['state']
                else:
                    new_donation.address_state = address['region']
                if 'zip' in address:  # US address
                    new_donation.address_postcode = address['zip']
                else:
                    new_donation.address_postcode = address['postcode']

            db.session.add(new_donation)
            db.session.commit()
            # TODO: Send receipt.

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
