from metabrainz.model import db
from metabrainz.donations.receipts import send_receipt
from flask import current_app
from wepay import WePay


class Donation(db.Model):
    __tablename__ = 'donation'

    id = db.Column(db.Integer, primary_key=True)

    # Personal details
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    moderator = db.Column(db.String)  # MusicBrainz username
    can_contact = db.Column('contact', db.Boolean, server_default='FALSE')
    anonymous = db.Column('anon', db.Boolean, server_default='FALSE')
    address_street = db.Column(db.String)
    address_city = db.Column(db.String)
    address_state = db.Column(db.String)
    address_postcode = db.Column(db.String)
    address_country = db.Column(db.String)

    # Transaction details
    timestamp = db.Column(db.DateTime, server_default='now()')
    transaction_id = db.Column('paypal_trans_id', db.String(32))
    amount = db.Column(db.Numeric(11, 2), nullable=False)
    fee = db.Column(db.Numeric(11, 2), nullable=False)
    memo = db.Column(db.String)

    @classmethod
    def add_donation(cls, first_name, last_name, email, amount, fee,
                     address_street=None, address_city=None, address_state=None,
                     address_postcode=None, address_country=None,
                     date=None, editor=None, can_contact=None, anonymous=None):
        new_donation = cls(
            first_name=first_name,
            last_name=last_name,
            email=email,
            moderator=editor,
            address_street=address_street,
            address_city=address_city,
            address_state=address_state,
            address_postcode=address_postcode,
            address_country=address_country,
            amount=amount,
            fee=fee,
            timestamp=date,
            can_contact=can_contact,
            anonymous=anonymous,
        )
        db.session.add(new_donation)
        db.session.commit()
        return new_donation

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

        # Only processing completed donations
        if form['payment_status'] != 'Completed':
            return

        # We shouldn't process transactions to address for payments
        if form['business'] == current_app.config['PAYPAL_BUSINESS']:
            return

        if form['receiver_email'] != current_app.config['PAYPAL_PRIMARY_EMAIL']:
            return

        if float(form['mc_gross']) < 0.50:
            return  # Tiny donation

        # Checking that txn_id has not been previously processed
        if cls.get_by_transaction_id(form['txn_id']) is not None:
            return

        new_donation = cls(
            first_name=form['first_name'],
            last_name=form['last_name'],
            email=form['payer_email'],
            moderator=form['custom'],
            address_street=form['address_street'],
            address_city=form['address_city'],
            address_state=form['address_state'],
            address_postcode=form['address_zip'],
            address_country=form['address_country'],
            amount=float(form['mc_gross']) - float(form['mc_fee']),
            fee=float(form['mc_fee']),
            transaction_id=form['txn_id'],
        )

        if 'option_name1' in form and 'option_name2' in form:
            if (form['option_name1'] == 'anonymous' and form['option_selection1'] == 'yes') or \
                    (form['option_name2'] == 'anonymous' and form['option_selection2'] == 'yes') or \
                            form['option_name2'] == 'yes':
                new_donation.anonymous = True
            if (form['option_name1'] == 'contact' and form['option_selection1'] == 'yes') or \
                    (form['option_name2'] == 'contact' and form['option_selection2'] == 'yes') or \
                            form['option_name2'] == 'yes':
                new_donation.can_contact = True

        db.session.add(new_donation)
        db.session.commit()

        send_receipt(
            new_donation.email,
            new_donation.timestamp,
            new_donation.amount,
            '%s %s' % (new_donation.first_name, new_donation.last_name),
            new_donation.moderator,
        )

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
            return True

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

            # TODO: Send receipt

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
