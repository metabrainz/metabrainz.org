from metabrainz.testing import FlaskTestCase
from metabrainz.model import payment
from metabrainz.model.payment import Payment
from metabrainz.model import db
from metabrainz.payments import Currency
from stripe import convert_to_stripe_object
from flask import current_app
import copy


class FakeStripeBalanceTransaction(object):
    @classmethod
    def retrieve(cls, bt_id):
        return convert_to_stripe_object(
            {
                "id": "txn_161MS22eZvKYlo2CD20DfbfM",
                "object": "balance_transaction",
                "amount": 4995,
                "currency": "usd",
                "net": 4820,
                "type": "charge",
                "created": 1431372030,
                "available_on": 1431907200,
                "status": "pending",
                "fee": 175,
                "fee_details": [
                    {
                        "amount": 175,
                        "currency": "usd",
                        "type": "stripe_fee",
                        "description": "Stripe processing fees",
                        "application": None
                    }
                ],
                "source": "ch_161MS22eZvKYlo2CcuXkbZS8",
                "description": "Donation to MetaBrainz Foundation",
                "sourced_transfers": {
                    "object": "list",
                    "total_count": 0,
                    "has_more": None,
                    "url": "/v1/transfers?source_transaction=ch_161MS22eZvKYlo2CcuXkbZS8",
                    "data": []
                }
            },
            api_key=None,
            account=None
        )


class PaymentModelGeneralTestCase(FlaskTestCase):
    """General tests for the Payment model."""

    def test_get_by_transaction_id(self):
        new = Payment()
        new.is_donation = True
        new.first_name = "Tester"
        new.last_name = "Testing"
        new.email = "test@example.org"
        new.transaction_id = "TEST"
        new.amount = 42.50
        new.currency = "eur"
        db.session.add(new)
        db.session.commit()

        result = Payment.get_by_transaction_id("TEST")
        self.assertIsNotNone(result)

        bad_result = Payment.get_by_transaction_id("MISSING")
        self.assertIsNone(bad_result)


class PaymentModelPayPalTestCase(FlaskTestCase):
    """PayPal-specific tests."""

    def setUp(self):
        super(PaymentModelPayPalTestCase, self).setUp()
        self.base_form = {
            # This is not a complete set of values:
            "first_name": "Tester",
            "last_name": "Testing",
            "custom": "tester",  # MusicBrainz username
            "payer_email": "test@example.org",
            "receiver_email": current_app.config["PAYPAL_ACCOUNT_IDS"]["USD"],
            "business": "donations@metabrainz.org",
            "address_street": "1 Main St",
            "address_city": "San Jose",
            "address_state": "CA",
            "address_country": "United States",
            "address_zip": "95131",
            "mc_currency": "USD",
            "mc_gross": "42.50",
            "mc_fee": "1",
            "txn_id": "TEST1",
            "payment_status": "Completed",

            # Additional variables:
            "option_name1": "anonymous",
            "option_selection1": "yes",
            "option_name2": "contact",
            "option_selection2": "yes",
        }

    def test_process_paypal_ipn(self):
        Payment.process_paypal_ipn(self.base_form)
        # Donation should be in the DB now
        payments = Payment.query.all()
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments[0].transaction_id, "TEST1")

        relatively_bad_form = copy.deepcopy(self.base_form)
        relatively_bad_form["txn_id"] = "TEST2"
        relatively_bad_form["mc_gross"] = "0.49"
        Payment.process_paypal_ipn(relatively_bad_form)
        # There should still be one recorded donation
        self.assertEqual(len(Payment.query.all()), 1)

        bad_form = copy.deepcopy(self.base_form)
        relatively_bad_form["txn_id"] = "TEST3"
        bad_form["business"] = current_app.config["PAYPAL_BUSINESS"]
        Payment.process_paypal_ipn(bad_form)
        # There should still be one recorded donation
        self.assertEqual(len(Payment.query.all()), 1)

        super_bad_form = copy.deepcopy(self.base_form)
        relatively_bad_form["txn_id"] = "TEST4"
        super_bad_form["payment_status"] = "Refunded"  # What kind of monster would do that?!
        Payment.process_paypal_ipn(super_bad_form)
        # There should still be one recorded donation
        self.assertEqual(len(Payment.query.all()), 1)

    def test_currency_case(self):
        """Try with different letter cases in the currency value."""
        form = copy.deepcopy(self.base_form)
        form["mc_currency"] = "UsD"
        Payment.process_paypal_ipn(form)
        payments = Payment.query.all()
        self.assertEqual(payments[0].currency, Currency.US_Dollar.value)

    def test_currency_euro(self):
        form = copy.deepcopy(self.base_form)
        form["mc_currency"] = "eur"
        Payment.process_paypal_ipn(form)
        payments = Payment.query.all()
        self.assertEqual(payments[0].currency, Currency.Euro.value)

    def test_unknown_currency(self):
        form = copy.deepcopy(self.base_form)
        form["mc_currency"] = "rub"
        Payment.process_paypal_ipn(form)
        payments = Payment.query.all()
        # Should ignore this payment notification
        self.assertEqual(len(payments), 0)


class PaymentModelStripeTestCase(FlaskTestCase):
    """Stripe-specific tests."""

    def setUp(self):
        super(PaymentModelStripeTestCase, self).setUp()
        payment.stripe.BalanceTransaction = FakeStripeBalanceTransaction

    def test_log_stripe_charge_donation(self):
        # Function should execute without any exceptions
        charge = convert_to_stripe_object(
            {
                "id": "ch_15AjX1F21qH57QtHT6avvqrM",
                "object": "charge",
                "created": 1418829367,
                "livemode": False,
                "paid": True,
                "status": "succeeded",
                "amount": 99999900,
                "currency": "usd",
                "refunded": False,
                "source": {
                    "id": "card_15AjWxF21qH57QtHHVNgaHOP",
                    "object": "card",
                    "last4": "4242",
                    "brand": "Visa",
                    "funding": "credit",
                    "exp_month": 11,
                    "exp_year": 2016,
                    "country": "US",
                    "name": "Uh Oh",
                    "address_line1": "test 12",
                    "address_line2": None,
                    "address_city": "Schenectady",
                    "address_state": "NY",
                    "address_zip": "12345",
                    "address_country": "United States",
                    "cvc_check": "pass",
                    "address_line1_check": "pass",
                    "address_zip_check": "pass",
                    "dynamic_last4": None,
                    "metadata": {},
                    "customer": None
                },
                "captured": True,
                "balance_transaction": "txn_159qthF21qH57QtHBksXX3tN",
                "failure_message": None,
                "failure_code": None,
                "amount_refunded": 0,
                "customer": None,
                "invoice": None,
                "description": "Donation to MetaBrainz Foundation",
                "dispute": None,
                "metadata": {
                    "is_donation": True,
                    "anonymous": "True",  # passed as a string
                    "can_contact": "False",  # passed as a string
                    "email": "mail@example.com",
                    "editor": "null"
                },
                "statement_descriptor": None,
                "fraud_details": {},
                "receipt_email": None,
                "receipt_number": None,
                "shipping": None,
                "application_fee": None,
                "refunds": {
                    "object": "list",
                    "total_count": 0,
                    "has_more": False,
                    "url": "/v1/charges/ch_15AjX1F21qH57QtHT6avvqrM/refunds",
                    "data": []
                }
            },
            api_key=None,
            account=None
        )
        Payment.log_stripe_charge(charge)
        self.assertEqual(len(Payment.query.all()), 1)

    def test_log_stripe_charge_payment(self):
        # Function should execute without any exceptions
        charge = convert_to_stripe_object(
            {
                "id": "ch_15AjX1F21qH57QtHT6avvqrM",
                "object": "charge",
                "created": 1418829367,
                "livemode": False,
                "paid": True,
                "status": "succeeded",
                "amount": 99999900,
                "currency": "usd",
                "refunded": False,
                "source": {
                    "id": "card_15AjWxF21qH57QtHHVNgaHOP",
                    "object": "card",
                    "last4": "4242",
                    "brand": "Visa",
                    "funding": "credit",
                    "exp_month": 11,
                    "exp_year": 2016,
                    "country": "US",
                    "name": "Uh Oh",
                    "address_line1": "test 12",
                    "address_line2": None,
                    "address_city": "Schenectady",
                    "address_state": "NY",
                    "address_zip": "12345",
                    "address_country": "United States",
                    "cvc_check": "pass",
                    "address_line1_check": "pass",
                    "address_zip_check": "pass",
                    "dynamic_last4": None,
                    "metadata": {},
                    "customer": None
                },
                "captured": True,
                "balance_transaction": "txn_159qthF21qH57QtHBksXX3tN",
                "failure_message": None,
                "failure_code": None,
                "amount_refunded": 0,
                "customer": None,
                "invoice": None,
                "description": "Donation to MetaBrainz Foundation",
                "dispute": None,
                "metadata": {
                    "is_donation": False,
                    "email": "mail@example.com",
                    "invoice_number": 42,
                },
                "statement_descriptor": None,
                "fraud_details": {},
                "receipt_email": None,
                "receipt_number": None,
                "shipping": None,
                "application_fee": None,
                "refunds": {
                    "object": "list",
                    "total_count": 0,
                    "has_more": False,
                    "url": "/v1/charges/ch_15AjX1F21qH57QtHT6avvqrM/refunds",
                    "data": []
                }
            },
            api_key=None,
            account=None
        )
        Payment.log_stripe_charge(charge)
        self.assertEqual(len(Payment.query.all()), 1)
