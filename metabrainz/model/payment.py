from __future__ import division
from metabrainz.model import db
from metabrainz.payments import Currency
from metabrainz.payments.receipts import send_receipt
from metabrainz.admin import AdminModelView
from sqlalchemy.sql import func, desc
from flask import current_app
from datetime import datetime
import stripe
import logging


PAYMENT_METHOD_STRIPE = 'stripe'
PAYMENT_METHOD_PAYPAL = 'paypal'
PAYMENT_METHOD_WEPAY = 'wepay'  # no longer supported
PAYMENT_METHOD_CHECK = 'check'


# These are defined in the `payment_currency` database type.
SUPPORTED_CURRENCIES = [code.value.lower() for code in Currency.__members__.values()]


class Payment(db.Model):
    __tablename__ = 'payment'

    id = db.Column(db.Integer, primary_key=True)

    # Personal details
    first_name = db.Column(db.Unicode, nullable=False)
    last_name = db.Column(db.Unicode, nullable=False)
    is_donation = db.Column(db.Boolean, nullable=False)
    email = db.Column(db.Unicode, nullable=False)
    address_street = db.Column(db.Unicode)
    address_city = db.Column(db.Unicode)
    address_state = db.Column(db.Unicode)
    address_postcode = db.Column(db.Unicode)
    address_country = db.Column(db.Unicode)

    # Donation-specific columns
    editor_name = db.Column(db.Unicode)  # MusicBrainz username
    can_contact = db.Column(db.Boolean)
    anonymous = db.Column(db.Boolean)

    # Organization-specific columns
    invoice_number = db.Column(db.Integer)

    # Transaction details
    payment_date = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    payment_method = db.Column(db.Enum(
        PAYMENT_METHOD_STRIPE,
        PAYMENT_METHOD_PAYPAL,
        PAYMENT_METHOD_WEPAY,  # legacy
        PAYMENT_METHOD_CHECK,
        name='payment_method_types'
    ))
    transaction_id = db.Column(db.Unicode)
    amount = db.Column(db.Numeric(11, 2), nullable=False)
    fee = db.Column(db.Numeric(11, 2))
    currency = db.Column(db.Enum(SUPPORTED_CURRENCIES, name='payment_currency'), nullable=False)
    memo = db.Column(db.Unicode)

    def __str__(self):
        return 'Payment #%s' % self.id

    @classmethod
    def get_by_transaction_id(cls, transaction_id):
        return cls.query.filter_by(transaction_id=str(transaction_id)).first()

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
            "SELECT ((amount + COALESCE(fee, 0)) * :days_per_dollar) - "
            "((extract(epoch from now()) - extract(epoch from payment_date)) / 86400) as nag "
            "FROM payment "
            "WHERE lower(editor_name) = lower(:editor) "
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
        query = cls.query.order_by(cls.payment_date.desc())
        query = query.filter(cls.is_donation == True)
        count = query.count()  # Total count should be calculated before limits
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
        return count, query.all()

    @classmethod
    def get_biggest_donations(cls, limit=None, offset=None):
        """Getter for biggest donations.

        Donations from the same person are grouped.

        Args:
            limit: Maximum number of donations to be returned.
            offset: Offset of the result.

        Returns:
            Tuple with two items. First is total number if donations. Second
            is a list of donations sorted by amount with a specified offset.
        """
        query = db.session.query(
            cls.first_name.label("first_name"),
            cls.last_name.label("last_name"),
            cls.editor_name.label("editor_name"),
            func.max(cls.payment_date).label("payment_date"),
            func.sum(cls.amount).label("amount"),
            func.sum(cls.fee).label("fee"),
        )
        query = query.filter(cls.is_donation == True)
        query = query.filter(cls.anonymous == False)
        query = query.group_by(cls.first_name, cls.last_name, cls.editor_name)
        query = query.order_by(desc("amount"))
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
        logging.debug('Processing PayPal IPN...')

        # Only processing completed donations
        if form['payment_status'] != 'Completed':
            logging.info('PayPal: Payment not completed. Status: "%s".', form['payment_status'])
            return

        account_ids = current_app.config['PAYPAL_ACCOUNT_IDS']  # "currency => account" mapping

        if form['mc_currency'].lower() not in SUPPORTED_CURRENCIES:
            logging.warning("Unsupported currency: ", form['mc_currency'])
            return

        # Checking if payment was sent to the right account depending on the currency
        if form['mc_currency'].upper() in account_ids:
            receiver_email_expected = current_app.config['PAYPAL_ACCOUNT_IDS'][form['mc_currency'].upper()]
            if receiver_email_expected != form['receiver_email']:
                logging.warning("Received {currency} payment to {addr} (expected {expected_addr})".format(
                                currency=form['mc_currency'],
                                addr=form['receiver_email'],
                                expected_addr=receiver_email_expected))

        # We shouldn't process transactions to address for payments
        # TODO: Clarify what this address is
        if form['business'] == current_app.config['PAYPAL_BUSINESS']:
            logging.info('PayPal: Received payment to address for payments.')
            return

        if form['receiver_email'] not in account_ids.values():
            logging.warning('PayPal: Unexpected receiver email. Got "%s".', form['receiver_email'])
            return
        if float(form['mc_gross']) < 0.50:
            # Tiny donation
            logging.info('PayPal: Tiny donation ($%s).', form['mc_gross'])
            return

        # Checking that txn_id has not been previously processed
        if cls.get_by_transaction_id(form['txn_id']) is not None:
            logging.info('PayPal: Transaction ID %s has been used before.', form['txn_id'])
            return

        if 'option_name3' in form and form['option_name3'] == "is_donation" \
                and form['option_selection3'] != 'yes':
            is_donation = False
        else:
            # If third option (whether it is donation or not) is not specified, assuming
            # that it is donation. This is done to support old IPN messages.
            is_donation = True

        new_payment = cls(
            is_donation=is_donation,
            first_name=form['first_name'],
            last_name=form['last_name'],
            email=form['payer_email'],
            address_street=form.get('address_street'),
            address_city=form.get('address_city'),
            address_state=form.get('address_state'),
            address_postcode=form.get('address_zip'),
            address_country=form.get('address_country'),
            amount=float(form['mc_gross']) - float(form['mc_fee']),
            fee=float(form['mc_fee']),
            transaction_id=form['txn_id'],
            currency=form['mc_currency'].lower(),
            payment_method=PAYMENT_METHOD_PAYPAL,
        )

        if is_donation:
            new_payment.editor_name = form.get('custom')
            if 'option_name1' in form and 'option_name2' in form:
                if (form['option_name1'] == 'anonymous' and form['option_selection1'] == 'yes') or \
                        (form['option_name2'] == 'anonymous' and form['option_selection2'] == 'yes') or \
                                form['option_name2'] == 'yes':
                    new_payment.anonymous = True
                if (form['option_name1'] == 'contact' and form['option_selection1'] == 'yes') or \
                        (form['option_name2'] == 'contact' and form['option_selection2'] == 'yes') or \
                                form['option_name2'] == 'yes':
                    new_payment.can_contact = True
        else:
            if 'option_name4' in form and form['option_name4'] == 'invoice_number':
                new_payment.invoice_number = int(form.get("option_selection4"))
            else:
                logging.warning("PayPal: Can't find invoice number if organization payment.")

        db.session.add(new_payment)
        db.session.commit()
        logging.info('PayPal: Payment added. ID: %s.', new_payment.id)

        send_receipt(
            email=new_payment.email,
            date=new_payment.payment_date,
            amount=new_payment.amount,
            name='%s %s' % (new_payment.first_name, new_payment.last_name),
            is_donation=new_payment.is_donation,
            editor_name=new_payment.editor_name,
        )

    @classmethod
    def log_stripe_charge(cls, charge):
        """Log successful Stripe charge.

        Args:
            charge: The charge object from Stripe. More information about it is
                available at https://stripe.com/docs/api/python#charge_object.
        """
        logging.debug('Processing Stripe charge...')

        bt = stripe.BalanceTransaction.retrieve(charge.balance_transaction)

        if bt.currency.lower() not in SUPPORTED_CURRENCIES:
            logging.warning("Unsupported currency: ", bt.currency)
            return

        new_donation = cls(
            first_name=charge.source.name,
            last_name='',
            amount=bt.net / 100,  # cents should be converted
            fee=bt.fee / 100,  # cents should be converted
            currency=bt.currency.lower(),
            transaction_id=charge.id,
            payment_method=PAYMENT_METHOD_STRIPE,

            is_donation=charge.metadata.is_donation,

            email=charge.metadata.email,
            address_street=charge.source.address_line1,
            address_city=charge.source.address_city,
            address_state=charge.source.address_state,
            address_postcode=charge.source.address_zip,
            address_country=charge.source.address_country,
        )

        if charge.metadata.is_donation is True or charge.metadata.is_donation == "True":
            new_donation.can_contact = charge.metadata.can_contact == u'True'
            new_donation.anonymous = charge.metadata.anonymous == u'True'
            if 'editor' in charge.metadata:
                new_donation.editor_name = charge.metadata.editor
        else:  # Organization payment
            new_donation.invoice_number = charge.metadata.invoice_number

        db.session.add(new_donation)
        db.session.commit()
        logging.info('Stripe: Payment added. ID: %s.', new_donation.id)

        send_receipt(
            email=new_donation.email,
            date=new_donation.payment_date,
            amount=new_donation.amount,
            name=new_donation.first_name,  # Last name is not used with Stripe
            is_donation=new_donation.is_donation,
            editor_name=new_donation.editor_name,
        )


class PaymentAdminView(AdminModelView):
    column_labels = dict(
        id='ID',
        is_donation='Donation',
        invoice_number='Invoice number',
        editor_name='MusicBrainz username',
        address_street='Street',
        address_city='City',
        address_state='State',
        address_postcode='Postal code',
        address_country='Country',
    )
    column_descriptions = dict(
        can_contact='This donor may be contacted',
        anonymous='This donor wishes to remain anonymous',
        amount='USD',
        fee='USD',
    )
    column_list = (
        'id',
        'email',
        'first_name',
        'last_name',
        'is_donation',
        'amount',
        'fee',
    )
    form_columns = (
        'first_name',
        'last_name',
        'email',
        'address_street',
        'address_city',
        'address_state',
        'address_postcode',
        'address_country',
        'amount',
        'fee',
        'memo',
        'is_donation',
        'invoice_number',
        'editor_name',
        'can_contact',
        'anonymous',
    )

    def __init__(self, session, **kwargs):
        super(PaymentAdminView, self).__init__(Payment, session, name='Payments', **kwargs)

    def after_model_change(self, form, new_donation, is_created):
        if is_created:
            send_receipt(
                email=new_donation.email,
                date=new_donation.payment_date,
                amount=new_donation.amount,
                name='%s %s' % (new_donation.first_name, new_donation.last_name),
                is_donation=new_donation.is_donation,
                editor_name=new_donation.editor_name,
            )
