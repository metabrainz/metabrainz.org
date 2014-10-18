from metabrainz.model import db
from flask import current_app
from wepay import WePay


class Donation(db.Model):
    __tablename__ = 'donation'

    id = db.Column(db.Integer, primary_key=True)

    # Personal details
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    moderator = db.Column(db.String, server_default='')
    can_contact = db.Column('contact', db.Boolean, server_default='FALSE')
    anonymous = db.Column('anon', db.Boolean, server_default='FALSE')
    address_street = db.Column(db.String, server_default='')
    address_city = db.Column(db.String, server_default='')
    address_state = db.Column(db.String, server_default='')
    address_postcode = db.Column(db.String, server_default='')
    address_country = db.Column(db.String, server_default='')

    # Transaction details
    timestamp = db.Column(db.DateTime, server_default='now()')
    transaction_id = db.Column('paypal_trans_id', db.String(32), nullable=False)
    amount = db.Column(db.Numeric(11, 2), nullable=False)
    fee = db.Column(db.String, server_default='')
    memo = db.Column(db.String, server_default='')

    @classmethod
    def get_by_transaction_id(cls, transaction_id):
        return cls.query.filter_by(transaction_id=transaction_id).first()

    @classmethod
    def process_paypal_ipn(cls, form):
        """Processor for PayPal IPNs (Instant Payment Notifications).

        Should be used only after IPN request is verified. See PayPal documentation for
        more info about the process.

        Args:
            form: The form parameters from IPN request that contains IPN variables.
                See https://developer.paypal.com/docs/classic/ipn/integration-guide/IPNandPDTVariables/
                for more info about them.
        """

        # Checking that txn_id has not been previously processed
        if cls.get_by_transaction_id(form['txn_id']) is not None:
            # Transaction ID used before
            pass

        # Checking that receiver_email is the primary PayPal email
        elif form['receiver_email'] != current_app.config['PAYPAL_PRIMARY_EMAIL']:
            # Not primary email
            pass

        elif form['mc_gross'] < 0.50:
            # Tiny donation
            pass

        elif form['payment_status'] == 'Completed' and form['business'] != current_app.config['PAYPAL_BUSINESS']:
            new_donation = cls(
                first_name=form['first_name'],
                last_name=form['last_name'],
                email=form['payer_email'],
                # TODO: Set custom variables like editor's name (moderator), anonymity, and contact preference.
                address_street=form['address_street'],
                address_city=form['address_city'],
                address_state=form['address_state'],
                address_zip=form['address_zip'],
                address_country=form['address_country'],
                amount=form['mc_gross']-form['mc_fee'],
                fee=form['mc_fee'],
                transaction_id=form['txn_id'],
            )
            db.session.add(new_donation)
            db.session.commit()
            # TODO: Send receipt.

        elif form['payment_status'] == 'Pending':
            # Payment is pending
            pass

        elif form['business'] == current_app.config['PAYPAL_BUSINESS']:
            # non donation received
            pass

        else:
            # Other status (no error)
            pass


    @classmethod
    def verify_and_log_wepay_checkout(cls, checkout_id, editor, anonymous, can_contact):
        # Looking up updated information about the object
        wepay = WePay(production=current_app.config['PAYMENT_PRODUCTION'],
                      access_token=current_app.config['WEPAY_ACCESS_TOKEN'])
        details = wepay.call('/checkout', {'checkout_id': checkout_id})

        if 'error' in details:
            return False

        if details['gross'] < 0.50:
            # Tiny donation
            pass

        elif details['state'] in ['settled', 'captured']:
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
                transaction_id=checkout_id,
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
