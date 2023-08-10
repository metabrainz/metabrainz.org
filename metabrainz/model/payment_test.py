from unittest.mock import patch

from metabrainz.testing import FlaskTestCase
from metabrainz.model.payment import Payment
from metabrainz.model import db
from metabrainz.payments import Currency
from flask import current_app
import copy
import stripe


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

    def test_extract_paypal_ipn_options(self):
        form = copy.deepcopy(self.base_form)
        self.assertDictEqual(Payment._extract_paypal_ipn_options(form), {
            "anonymous": "yes",
            "contact": "yes",
        })

        self.assertDictEqual(Payment._extract_paypal_ipn_options({
            "option_name1": "contact",
            "option_name2": "anonymous",
            "option_name3": "is_donation",
            "option_selection1": "N/A",
            "option_selection2": "yes",
            "option_selection3": "yes",
        }), {
            "contact": "N/A",
            "anonymous": "yes",
            "is_donation": "yes",
        })


class PaymentModelStripeTestCase(FlaskTestCase):
    """Stripe-specific tests."""

    def setUp(self):
        super(PaymentModelStripeTestCase, self).setUp()
        self.session_without_metadata = {
            "id": "cs_test_a1sNH4THpeTEp9qwePCKNI3A9f2r6Li",
            "object": "checkout.session",
            "after_expiration": None,
            "allow_promotion_codes": None,
            "amount_subtotal": 15000,
            "amount_total": 15000,
            "automatic_tax": {
                "enabled": False,
                "status": None
            },
            "billing_address_collection": "required",
            "cancel_url": "http://localhost:8000/payment/cancelled?is_donation=True",
            "client_reference_id": None,
            "consent": None,
            "consent_collection": None,
            "currency": "usd",
            "customer": "cus_KSHNduYk",
            "customer_details": {
                "email": "testing@gmail.com",
                "phone": None,
                "tax_exempt": "none",
                "tax_ids": [
                ]
            },
            "customer_email": None,
            "expires_at": 1634991912,
            "livemode": False,
            "locale": None,
            "mode": "payment",
            "payment_intent": "pi_3JnMoZB",
            "payment_method_options": {
            },
            "payment_method_types": [
                "card"
            ],
            "payment_status": "paid",
            "phone_number_collection": {
                "enabled": False
            },
            "recovered_from": None,
            "setup_intent": None,
            "shipping": None,
            "shipping_address_collection": None,
            "submit_type": "donate",
            "subscription": None,
            "success_url": "http://localhost:8000/payment/complete?is_donation=True",
            "total_details": {
                "amount_discount": 0,
                "amount_shipping": 0,
                "amount_tax": 0
            },
            "url": None
        }
        self.payment_intent = {
            "amount": 15000,
            "amount_capturable": 0,
            "amount_received": 15000,
            "application": None,
            "application_fee_amount": None,
            "canceled_at": None,
            "cancellation_reason": None,
            "capture_method": "automatic",
            "charges": {
                "data": [
                    {
                        "amount": 15000,
                        "amount_captured": 15000,
                        "amount_refunded": 0,
                        "application": None,
                        "application_fee": None,
                        "application_fee_amount": None,
                        "balance_transaction": {
                            "amount": 1100526,
                            "available_on": 1635465600,
                            "created": 1634905541,
                            "cross_border_classification": "export",
                            "currency": "usd",
                            "description": None,
                            "exchange_rate": 73.3684,
                            "fee": 55841,
                            "fee_details": [
                                {
                                    "amount": 8518,
                                    "application": None,
                                    "currency": "usd",
                                    "description": "GST",
                                    "type": "tax"
                                },
                                {
                                    "amount": 47323,
                                    "application": None,
                                    "currency": "usd",
                                    "description": "Stripe processing fees",
                                    "type": "stripe_fee"
                                }
                            ],
                            "id": "txn_3JnMFzLHJk1rdonaIW",
                            "net": 1044685,
                            "object": "balance_transaction",
                            "reporting_category": "charge",
                            "source": "ch_3JnMo8SIg1ZpIFTmV",
                            "status": "pending",
                            "type": "charge"
                        },
                        "billing_details": {
                            "address": {
                                "city": "Doesn't Matter",
                                "country": "GL",
                                "line1": "Any value",
                                "line2": None,
                                "postal_code": "46071",
                                "state": None
                            },
                            "email": "testing@gmail.com",
                            "name": "Lucifer",
                            "phone": None
                        },
                        "calculated_statement_descriptor": "LUCIFERTESTINGACCOUNT",
                        "captured": True,
                        "created": 1634905541,
                        "currency": "usd",
                        "customer": "cus_KSHNuduYk",
                        "description": None,
                        "destination": None,
                        "dispute": None,
                        "disputed": False,
                        "failure_code": None,
                        "failure_message": None,
                        "fraud_details": {},
                        "id": "ch_3JnMo8SIgvFzTmV",
                        "invoice": None,
                        "livemode": False,
                        "metadata": {},
                        "object": "charge",
                        "on_behalf_of": None,
                        "order": None,
                        "outcome": {
                            "network_status": "approved_by_network",
                            "reason": None,
                            "risk_level": "normal",
                            "risk_score": 7,
                            "seller_message": "Payment complete.",
                            "type": "authorized"
                        },
                        "paid": True,
                        "payment_intent": "pi_3JnMo8SFAoSPZBEYj80Aa",
                        "payment_method": "pm_1JnMoZSFzLHJk1KzLHktn",
                        "payment_method_details": {
                            "card": {
                                "brand": "visa",
                                "checks": {
                                    "address_line1_check": "pass",
                                    "address_postal_code_check": "pass",
                                    "cvc_check": "pass"
                                },
                                "country": "US",
                                "exp_month": 2,
                                "exp_year": 2026,
                                "fingerprint": "vChIMFgq3Ve",
                                "funding": "credit",
                                "installments": None,
                                "last4": "4242",
                                "network": "visa",
                                "three_d_secure": {
                                    "authentication_flow": None,
                                    "result": "attempt_acknowledged",
                                    "result_reason": None,
                                    "version": "1.0.2"
                                },
                                "wallet": None
                            },
                            "type": "card"
                        },
                        "receipt_email": None,
                        "receipt_number": None,
                        "receipt_url": "https://pay.stripe.com/receipts/acct_1JjJe3FzLHJk/ch_SIgvzLHJk1ZpIFTmV/rcpt_xUaDGQsPmfrc4J1NEBohQbvS0W",
                        "refunded": False,
                        "refunds": {
                            "data": [],
                            "has_more": False,
                            "object": "list",
                            "total_count": 0,
                            "url": "/v1/charges/ch_3SIgLHJk1ZpIFTmV/refunds"
                        },
                        "review": None,
                        "shipping": None,
                        "source": None,
                        "source_transfer": None,
                        "statement_descriptor": None,
                        "statement_descriptor_suffix": None,
                        "status": "succeeded",
                        "transfer_data": None,
                        "transfer_group": None
                    }
                ],
                "has_more": False,
                "object": "list",
                "total_count": 1,
                "url": "/v1/charges?payment_intent=pi_3JnMo8SIHJk1oSPZB"
            },
            "client_secret": "pi_3JnMo8SIgzLHPZB_secret_OuVctwTNvmXf6XUON",
            "confirmation_method": "automatic",
            "created": 1634905512,
            "currency": "usd",
            "customer": "cus_KSHVduduYk",
            "description": None,
            "id": "pi_3JnMo8SIgvSPZB",
            "invoice": None,
            "last_payment_error": None,
            "livemode": False,
            "metadata": {},
            "next_action": None,
            "object": "payment_intent",
            "on_behalf_of": None,
            "payment_method": "pm_1JnMoZSIgvtnEYj80A",
            "payment_method_options": {
                "card": {
                    "installments": None,
                    "network": None,
                    "request_three_d_secure": "automatic"
                }
            },
            "payment_method_types": [
                "card"
            ],
            "receipt_email": None,
            "review": None,
            "setup_future_usage": None,
            "shipping": None,
            "source": None,
            "statement_descriptor": None,
            "statement_descriptor_suffix": None,
            "status": "succeeded",
            "transfer_data": None,
            "transfer_group": None
        }

    @patch("stripe.PaymentIntent")
    def test_log_stripe_charge_donation(self, mock_stripe):
        # Function should execute without any exceptions
        payment_intent = self.payment_intent.copy()
        payment_intent["metadata"] = {
            "is_donation": "True",
            "editor": "lucifer",
            "anonymous": "False",
            "can_contact": "False"
        }
        mock_stripe.retrieve.return_value = payment_intent
        session = self.session_without_metadata.copy()
        Payment.log_one_time_charge(session)
        self.assertEqual(len(Payment.query.all()), 1)

    @patch("stripe.PaymentIntent")
    def test_log_stripe_charge_payment(self, mock_stripe):
        # Function should execute without any exceptions
        payment_intent = self.payment_intent.copy()
        payment_intent["metadata"] = {
            "is_donation": "False",
            "email": "mail@example.com",
            "invoice_number": 42,
        }
        mock_stripe.retrieve.return_value = payment_intent
        Payment.log_one_time_charge(self.session_without_metadata)
        self.assertEqual(len(Payment.query.all()), 1)
