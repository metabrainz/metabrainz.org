import copy
from unittest.mock import patch

from flask import current_app

from metabrainz.model import db
from metabrainz.model.payment import Payment
from metabrainz.payments import Currency
from metabrainz.testing import FlaskTestCase


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
            "id": "cs_test_a1Xnl40m2FIdI4qWQme3Sy2gPd2RnA4D764BqtueKvQC0sCfkQbWPnkZeU",
            "object": "checkout.session",
            "after_expiration": None,
            "allow_promotion_codes": None,
            "amount_subtotal": 5000,
            "amount_total": 5000,
            "automatic_tax": {
                "enabled": False,
                "liability": None,
                "status": None
            },
            "billing_address_collection": "required",
            "cancel_url": "https://test.metabrainz.org/payment/cancelled?is_donation=True",
            "client_reference_id": None,
            "client_secret": None,
            "consent": None,
            "consent_collection": None,
            "created": 1721063848,
            "currency": "usd",
            "currency_conversion": None,
            "custom_fields": [
            ],
            "custom_text": {
                "after_submit": None,
                "shipping_address": None,
                "submit": None,
                "terms_of_service_acceptance": None
            },
            "customer": None,
            "customer_creation": "if_required",
            "customer_details": {
                "address": {
                    "city": "Delhi",
                    "country": "IN",
                    "line1": "Chandni Chowk",
                    "line2": None,
                    "postal_code": "110006",
                    "state": "DL"
                },
                "email": "test@gmail.com",
                "name": "Lucifer",
                "phone": None,
                "tax_exempt": "none",
                "tax_ids": [
                ]
            },
            "customer_email": None,
            "expires_at": 1721150248,
            "invoice": None,
            "invoice_creation": {
                "enabled": False,
                "invoice_data": {
                    "account_tax_ids": None,
                    "custom_fields": None,
                    "description": None,
                    "footer": None,
                    "issuer": None,
                    "metadata": {
                    },
                    "rendering_options": None
                }
            },
            "livemode": False,
            "locale": None,
            "metadata": {
            },
            "mode": "payment",
            "payment_intent": "pi_3PcsXqISlclrXlsU1mOuLu09",
            "payment_link": None,
            "payment_method_collection": "if_required",
            "payment_method_configuration_details": None,
            "payment_method_options": {
                "card": {
                    "request_three_d_secure": "automatic"
                }
            },
            "payment_method_types": [
                "card"
            ],
            "payment_status": "paid",
            "phone_number_collection": {
                "enabled": False
            },
            "recovered_from": None,
            "saved_payment_method_options": None,
            "setup_intent": None,
            "shipping": None,
            "shipping_address_collection": None,
            "shipping_options": [
            ],
            "shipping_rate": None,
            "status": "complete",
            "submit_type": "donate",
            "subscription": None,
            "success_url": "https://test.metabrainz.org/payment/complete?is_donation=True",
            "total_details": {
                "amount_discount": 0,
                "amount_shipping": 0,
                "amount_tax": 0
            },
            "ui_mode": "hosted",
            "url": None
        }
        self.payment_intent = {
            "amount": 5000,
            "amount_capturable": 0,
            "amount_details": {
                "tip": {}
            },
            "amount_received": 5000,
            "application": None,
            "application_fee_amount": None,
            "automatic_payment_methods": None,
            "canceled_at": None,
            "cancellation_reason": None,
            "capture_method": "automatic",
            "client_secret": "",
            "confirmation_method": "automatic",
            "created": 1721063918,
            "currency": "usd",
            "customer": None,
            "description": "Donation to the MetaBrainz Foundation",
            "id": "pi_3PcsXqISlclrXlsU1mOuLu09",
            "invoice": None,
            "last_payment_error": None,
            "latest_charge": {
                "amount": 5000,
                "amount_captured": 5000,
                "amount_refunded": 0,
                "application": None,
                "application_fee": None,
                "application_fee_amount": None,
                "balance_transaction": {
                    "amount": 5000,
                    "available_on": 1721174400,
                    "created": 1721063919,
                    "currency": "usd",
                    "description": "Donation to the MetaBrainz Foundation",
                    "exchange_rate": None,
                    "fee": 175,
                    "fee_details": [
                        {
                            "amount": 175,
                            "application": None,
                            "currency": "usd",
                            "description": "Stripe processing fees",
                            "type": "stripe_fee"
                        }
                    ],
                    "id": "txn_3PcsXqISlclrXlsU1eOyDsoF",
                    "net": 4825,
                    "object": "balance_transaction",
                    "reporting_category": "charge",
                    "source": "ch_3PcsXqISlclrXlsU1OR5YDF6",
                    "status": "pending",
                    "type": "charge"
                },
                "billing_details": {
                    "address": {
                        "city": "Delhi",
                        "country": "IN",
                        "line1": "Chandni Chowk",
                        "line2": None,
                        "postal_code": "110006",
                        "state": "DL"
                    },
                    "email": "kartikohri13@gmail.com",
                    "name": "KARTIK OHRI",
                    "phone": None
                },
                "calculated_statement_descriptor": "METABRAINZ FOUNDATION",
                "captured": True,
                "created": 1721063919,
                "currency": "usd",
                "customer": None,
                "description": "Donation to the MetaBrainz Foundation",
                "destination": None,
                "dispute": None,
                "disputed": False,
                "failure_balance_transaction": None,
                "failure_code": None,
                "failure_message": None,
                "fraud_details": {},
                "id": "ch_3PcsXqISlclrXlsU1OR5YDF6",
                "invoice": None,
                "livemode": False,
                "metadata": {
                    "anonymous": "False",
                    "can_contact": "False",
                    "editor": "lucifer",
                    "is_donation": "True"
                },
                "object": "charge",
                "on_behalf_of": None,
                "order": None,
                "outcome": {
                    "network_status": "approved_by_network",
                    "reason": None,
                    "risk_level": "normal",
                    "risk_score": 38,
                    "seller_message": "Payment complete.",
                    "type": "authorized"
                },
                "paid": True,
                "payment_intent": "pi_3PcsXqISlclrXlsU1mOuLu09",
                "payment_method": "pm_1PcsXpISlclrXlsUAKE1YVd2",
                "payment_method_details": {
                    "card": {
                        "amount_authorized": 5000,
                        "brand": "visa",
                        "checks": {
                            "address_line1_check": "pass",
                            "address_postal_code_check": "pass",
                            "cvc_check": "pass"
                        },
                        "country": "US",
                        "exp_month": 1,
                        "exp_year": 2026,
                        "extended_authorization": {
                            "status": "disabled"
                        },
                        "fingerprint": "4mEB6pJ8j7eJWcK2",
                        "funding": "credit",
                        "incremental_authorization": {
                            "status": "unavailable"
                        },
                        "installments": None,
                        "last4": "4242",
                        "mandate": None,
                        "multicapture": {
                            "status": "unavailable"
                        },
                        "network": "visa",
                        "network_token": {
                            "used": False
                        },
                        "overcapture": {
                            "maximum_amount_capturable": 5000,
                            "status": "unavailable"
                        },
                        "three_d_secure": None,
                        "wallet": None
                    },
                    "type": "card"
                },
                "radar_options": {},
                "receipt_email": None,
                "receipt_number": None,
                "receipt_url": "",
                "refunded": False,
                "review": None,
                "shipping": None,
                "source": None,
                "source_transfer": None,
                "statement_descriptor": None,
                "statement_descriptor_suffix": None,
                "status": "succeeded",
                "transfer_data": None,
                "transfer_group": None
            },
            "livemode": False,
            "metadata": {
                "anonymous": "False",
                "can_contact": "False",
                "editor": "lucifer",
                "is_donation": "True"
            },
            "next_action": None,
            "object": "payment_intent",
            "on_behalf_of": None,
            "payment_method": "pm_1PcsXpISlclrXlsUAKE1YVd2",
            "payment_method_configuration_details": None,
            "payment_method_options": {
                "card": {
                    "installments": None,
                    "mandate_options": None,
                    "network": None,
                    "request_three_d_secure": "automatic"
                }
            },
            "payment_method_types": [
                "card"
            ],
            "processing": None,
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
        Payment.log_one_time_charge("usd", session)
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
        Payment.log_one_time_charge("usd", self.session_without_metadata)
        self.assertEqual(len(Payment.query.all()), 1)
