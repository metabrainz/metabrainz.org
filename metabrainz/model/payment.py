from __future__ import division
from metabrainz.model import db
from metabrainz.payments import Currency, SUPPORTED_CURRENCIES
from metabrainz.payments.receipts import send_receipt
from metabrainz.admin import AdminModelView
from sentry_sdk import capture_message
from sqlalchemy.sql import func, desc
from flask import current_app
from datetime import datetime
import stripe
import logging


PAYMENT_METHOD_STRIPE = 'stripe'
PAYMENT_METHOD_PAYPAL = 'paypal'
PAYMENT_METHOD_WEPAY = 'wepay'  # no longer supported
PAYMENT_METHOD_CHECK = 'check'


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
    currency = db.Column(
        db.Enum(
            Currency.US_Dollar.value,
            Currency.Euro.value,
            name='payment_currency'
        ),
        nullable=False,
        default='usd',
    )
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
            # TODO(roman): Convert to regular `logging.info` call when such detailed logs
            # are no longer necessary to capture.
            capture_message("PayPal: Payment is not completed", level="info", extra={"ipn_content": form})
            return

        account_ids = current_app.config['PAYPAL_ACCOUNT_IDS']  # "currency => account" mapping

        if form['mc_currency'].lower() not in SUPPORTED_CURRENCIES:
            logging.warning("PayPal IPN: Unsupported currency", extra={"ipn_content": form})
            return

        # We shouldn't process transactions to address for payments
        # TODO: Clarify what this address is
        if form['business'] == current_app.config['PAYPAL_BUSINESS']:
            logging.info('PayPal: Received payment to address for payments.', extra={"ipn_content": form})
            return

        # Checking if payment was sent to the right account depending on the currency
        if form['mc_currency'].upper() in account_ids:
            receiver_email_expected = current_app.config['PAYPAL_ACCOUNT_IDS'][form['mc_currency'].upper()]
            if receiver_email_expected != form['receiver_email']:
                logging.warning("Received payment to an unexpected address", extra={
                    "currency": form['mc_currency'],
                    "received_to_address": form['receiver_email'],
                    "expected_address": receiver_email_expected,
                    "ipn_content": form,
                })
        if form['receiver_email'] not in account_ids.values():
            logging.warning('PayPal: Unexpected receiver email', extra={
                "received_to_address": form['receiver_email'],
                "ipn_content": form,
            })

        if float(form['mc_gross']) < 0.50:
            # Tiny donation
            logging.info('PayPal: Tiny donation', extra={"ipn_content": form})
            return

        # Checking that txn_id has not been previously processed
        if cls.get_by_transaction_id(form['txn_id']) is not None:
            logging.info('PayPal: Transaction ID has been used before', extra={
                "transaction_id": form['txn_id'],
                "ipn_content": form,
            })
            return

        options = cls._extract_paypal_ipn_options(form)

        # If donation option (whether it is donation or not) is not specified, assuming
        # that this payment is donation. This is done to support old IPN messages.
        is_donation = options.get("is_donation", "yes") == "yes"

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

            anonymous_opt = options.get("anonymous")
            if anonymous_opt is None:
                logging.warning("PayPal: Anonymity option is missing", extra={"ipn_content": form})
            else:
                new_payment.anonymous = anonymous_opt == "yes"

            contact_opt = options.get("contact")
            if contact_opt is None:
                logging.warning("PayPal: Contact option is missing", extra={"ipn_content": form})
            else:
                new_payment.can_contact = contact_opt == "yes"

        else:
            invoice_num_opt = options.get("invoice_number")
            if invoice_num_opt is None:
                logging.warning("PayPal: Invoice number is missing from org payment", extra={"ipn_content": form})
            else:
                new_payment.invoice_number = int(invoice_num_opt)

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

    @staticmethod
    def _extract_paypal_ipn_options(form: dict) -> dict:
        """Extracts all options from a PayPal IPN.
        
        This is necessary because the order or numbering of options might not
        what you expect it to be.
         
        Returns:
            Dictionary that maps options (by name) to their values.
        """
        options = {}
        current_number = 1  # option numbering starts from 1, not 0
        while True:
            current_key = "option_name" + str(current_number)
            current_val = "option_selection" + str(current_number)
            if current_key not in form:
                break
            if current_val not in form:
                logging.warning("PayPal: Value for option `{name}` is missing".format(name=current_key),
                                extra={"ipn_content": form})
            options[form[current_key]] = form[current_val]
            current_number += 1
        return options

    @classmethod
    def log_stripe_charge(cls, session):
        """Log successful Stripe charge.

        Args:
            session: The charge object from Stripe. More information about it is
                available at https://stripe.com/docs/api/python#charge_object.
        """
        logging.debug("Processing Stripe charge...")
        metadata = session["metadata"]

        payment_intent = stripe.PaymentIntent.retrieve(session["payment_intent"],
                                                       expand=["charges.data.balance_transaction"])
        charge = payment_intent["charges"]["data"][0]

        details = charge["billing_details"]
        address = details["address"]

        transaction = charge["balance_transaction"]
        currency = transaction["currency"].lower()
        if currency not in SUPPORTED_CURRENCIES:
            logging.warning("Unsupported currency: ", session["currency"])
            return

        new_donation = cls(
            first_name=details["name"],
            last_name="",
            amount=transaction["net"] / 100,  # cents should be converted
            fee=transaction["fee"] / 100,  # cents should be converted
            currency=currency,
            transaction_id=charge["id"],
            payment_method=PAYMENT_METHOD_STRIPE,
            is_donation=metadata["is_donation"],
            email=details["email"],
            address_street=address["line1"],  # TODO: stripe also gives line2, should we use it?
            address_city=address["city"],
            address_state=address["state"],
            address_postcode=address["postal_code"],
            address_country=address["country"],
        )

        if metadata["is_donation"] == "True":
            new_donation.is_donation = 1
        if metadata["is_donation"] == "False":
            new_donation.is_donation = 0

        if new_donation.is_donation:
            if session.metadata.can_contact:
                new_donation.can_contact = 1
            else:
                new_donation.can_contact = 0
            if session.metadata.anonymous:
                new_donation.anonymous = 1
            else:
                new_donation.anonymous = 0

            if "editor" in metadata:
                new_donation.editor_name = metadata["editor"]
        else:  # Organization payment
            new_donation.invoice_number = metadata["invoice_number"]

        db.session.add(new_donation)
        try:
            db.session.commit()
            logging.info("Stripe: Payment added. ID: %s.", new_donation.id)
        except TypeError as err:
            logging.error("Cannot record payment: ", err)

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
        'payment_date',
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
