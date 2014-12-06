from metabrainz.model import db
from metabrainz.donations.receipts import send_receipt
from flask import current_app
from flask_admin.contrib.sqla import ModelView
from wepay import WePay
from datetime import datetime


class Donation(db.Model):
    __tablename__ = 'donation'

    id = db.Column(db.Integer, primary_key=True)

    # Personal details
    first_name = db.Column(db.Unicode, nullable=False)
    last_name = db.Column(db.Unicode, nullable=False)
    email = db.Column(db.Unicode, nullable=False)
    mb_username = db.Column(db.String)  # MusicBrainz username
    can_contact = db.Column('contact', db.Boolean, server_default='FALSE')
    anonymous = db.Column('anon', db.Boolean, server_default='FALSE')
    address_street = db.Column(db.Unicode)
    address_city = db.Column(db.Unicode)
    address_state = db.Column(db.Unicode)
    address_postcode = db.Column(db.Unicode)
    address_country = db.Column(db.Unicode)

    # Transaction details
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    transaction_id = db.Column('paypal_trans_id', db.String(32))
    amount = db.Column(db.Numeric(11, 2), nullable=False)
    fee = db.Column(db.Numeric(11, 2), nullable=False, default=0)
    memo = db.Column(db.Unicode)

    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))  # Organization that made this donation

    def __unicode__(self):
        return 'Donation #%s' % self.id

    @classmethod
    def add_donation(cls, first_name, last_name, email, amount, fee=0,
                     address_street=None, address_city=None, address_state=None,
                     address_postcode=None, address_country=None,
                     payment_date=None, editor=None, can_contact=None, anonymous=None):
        new_donation = cls(
            first_name=first_name,
            last_name=last_name,
            email=email,
            mb_username=editor,
            address_street=address_street,
            address_city=address_city,
            address_state=address_state,
            address_postcode=address_postcode,
            address_country=address_country,
            amount=amount,
            fee=fee,
            payment_date=payment_date,
            can_contact=can_contact,
            anonymous=anonymous,
        )
        db.session.add(new_donation)
        db.session.commit()
        return new_donation

    @classmethod
    def get_by_transaction_id(cls, transaction_id):
        return cls.query.filter_by(transaction_id=transaction_id).first()

    @staticmethod
    def get_nag_days(editor):
        """

        Returns:
            Two values. First one indicates if editor should be nagged:
            -1 = unknown person, 0 = no need to nag, 1 = should be nagged.
            Second is...
        """
        days_per_dollar = 7.5
        result = db.session.execute(
            "SELECT ((amount + fee) * :days_per_dollar) - "
            "((extract(epoch from now()) - extract(epoch from payment_date)) / 86400) as nag "
            "FROM donation "
            "WHERE lower(mb_username) = lower(:editor) "
            "ORDER BY nag DESC "
            "LIMIT 1",
            {'editor': editor, 'days_per_dollar': days_per_dollar}
        ).fetchone()

        if result is None:
            return -1, 0
        elif result[0] >= 0:
            return 0, result[0]
        else:
            return 1, result[0]

    @classmethod
    def get_recent_donations(cls, limit=None, offset=None):
        """Getter for most recent donations.

        Args:
            limit: Maximum number of donations to be returned.
            offset: Offset of the result.

        Returns:
            Tuple with two items. First is total number if donations. Second
            is a list of donations sorted by payment_date with a specified offset.
        """
        query = cls.query.order_by(cls.payment_date)
        count = query.count()  # Total count should be calculated before limits
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
        return count, query.all()

    @classmethod
    def get_biggest_donations(cls, limit=None, offset=None):
        """Getter for biggest donations.

        Args:
            limit: Maximum number of donations to be returned.
            offset: Offset of the result.

        Returns:
            Tuple with two items. First is total number if donations. Second
            is a list of donations sorted by amount with a specified offset.
        """
        query = cls.query.order_by(-cls.amount)
        count = query.count()  # Total count should be calculated before limits
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
        return count, query.all()

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
            mb_username=form['custom'],
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
            new_donation.payment_date,
            new_donation.amount,
            '%s %s' % (new_donation.first_name, new_donation.last_name),
            new_donation.mb_username,
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
                mb_username=editor,
                can_contact=can_contact,
                anonymous=anonymous,
                amount=details['gross'] - details['fee'],
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

            send_receipt(
                new_donation.email,
                new_donation.payment_date,
                new_donation.amount,
                '%s %s' % (new_donation.first_name, new_donation.last_name),
                new_donation.mb_username,
            )

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


class DonationAdminView(ModelView):
    column_labels = dict(
        id='ID',
        mb_username='MusicBrainz username',
        address_street='Street',
        address_city='City',
        address_state='State',
        address_postcode='Postal code',
        address_country='Country',
    )
    column_descriptions = dict(
        organization='Organization associated with this donation',
        can_contact='This donor may be contacted',
        anonymous='This donor wishes to remain anonymous',
        amount='USD',
        fee='USD',
    )
    column_list = ('id', 'email', 'first_name', 'last_name', 'amount', 'fee',)
    form_columns = (
        'first_name', 'last_name', 'email', 'address_street', 'address_city',
        'address_state', 'address_postcode', 'address_country', 'amount', 'fee',
        'payment_date', 'organization', 'memo', 'can_contact', 'anonymous',
    )

    def __init__(self, session, **kwargs):
        super(DonationAdminView, self).__init__(Donation, session, name='Donations', **kwargs)
