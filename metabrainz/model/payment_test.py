# -*- coding: utf-8 -*-
from metabrainz.testing import FlaskTestCase
from metabrainz.model import payment
from metabrainz.model.payment import Payment
from metabrainz.model import db
from stripe import convert_to_stripe_object
from flask import url_for, current_app


class FakeWePay(object):

    def __init__(self, production=True, access_token=None, api_version=None):
        self.production = production
        self.access_token = access_token
        self.api_version = api_version

    def call(self, uri, params=None, token=None):
        if uri == '/checkout':
            return {
                'checkout_id': params['checkout_id'],
                'account_id': 54321,
                'state': u'captured',
                'soft_descriptor': u'MetaBrainz Donation',
                'short_description': u'Donation to MetaBrainz Foundation',
                'currency': u'USD',
                'amount': 100,
                'fee': 3.2,
                'gross': 108.2,
                'app_fee': 5,
                'shipping_fee': 5,
                'fee_payer': u'payer',
                'reference_id': u'abc123',
                'redirect_uri': url_for(
                    'payments.complete',
                    _external=True,
                    _scheme=current_app.config['PREFERRED_URL_SCHEME'],
                ),
                'callback_uri': url_for(
                    'payments_wepay.ipn',
                    _scheme=current_app.config['PREFERRED_URL_SCHEME'],
                    _external=True,
                    editor=u'Tester',
                    anonymous=False,
                    can_contact=True,
                ),
                'payer_email': u'test@example.org',
                'payer_name': u'Tester Testing',
                'auto_capture': True,
            }
        else:
            raise NotImplementedError()


class FakeStripeBalanceTransaction(object):
    @classmethod
    def retrieve(cls, bt_id):
        return convert_to_stripe_object(
            {
                "id": u"txn_161MS22eZvKYlo2CD20DfbfM",
                "object": u"balance_transaction",
                "amount": 4995,
                "currency": u"usd",
                "net": 4820,
                "type": u"charge",
                "created": 1431372030,
                "available_on": 1431907200,
                "status": u"pending",
                "fee": 175,
                "fee_details": [
                    {
                        "amount": 175,
                        "currency": u"usd",
                        "type": u"stripe_fee",
                        "description": u"Stripe processing fees",
                        "application": None
                    }
                ],
                "source": u"ch_161MS22eZvKYlo2CcuXkbZS8",
                "description": u"Donation to MetaBrainz Foundation",
                "sourced_transfers": {
                    "object": "list",
                    "total_count": 0,
                    "has_more": None,
                    "url": u"/v1/transfers?source_transaction=ch_161MS22eZvKYlo2CcuXkbZS8",
                    "data": []
                }
            },
            api_key=None,
            account=None
        )


class PaymentModelTestCase(FlaskTestCase):

    def setUp(self):
        super(PaymentModelTestCase, self).setUp()
        payment.WePay = lambda production=True, access_token=None, api_version=None: \
            FakeWePay(production, access_token, api_version)
        payment.stripe.BalanceTransaction = FakeStripeBalanceTransaction

    def test_get_by_transaction_id(self):
        new = Payment()
        new.is_donation = True
        new.first_name = u'Tester'
        new.last_name = u'Testing'
        new.email = u'test@example.org'
        new.transaction_id = u'TEST'
        new.amount = 42.50
        db.session.add(new)
        db.session.commit()

        result = Payment.get_by_transaction_id(u'TEST')
        self.assertIsNotNone(result)

        bad_result = Payment.get_by_transaction_id(u'MISSING')
        self.assertIsNone(bad_result)

    def test_process_paypal_ipn(self):
        # This is not a complete list:
        good_form = {
            'first_name': u'Tester',
            'last_name': u'Testing',
            'custom': u'tester',  # MusicBrainz username
            'payer_email': u'test@example.org',
            'receiver_email': current_app.config['PAYPAL_PRIMARY_EMAIL'],
            'business': u'donations@metabrainz.org',
            'address_street': u'1 Main St',
            'address_city': u'San Jose',
            'address_state': u'CA',
            'address_country': u'United States',
            'address_zip': u'95131',
            'mc_gross': u'42.50',
            'mc_fee': u'1',
            'txn_id': u'TEST1',
            'payment_status': u'Completed',

            # Additional variables:
            'option_name1': u'anonymous',
            'option_selection1': u'yes',
            'option_name2': u'contact',
            'option_selection2': u'yes',
        }
        Payment.process_paypal_ipn(good_form)
        # Donation should be in the DB now
        self.assertEqual(len(Payment.query.all()), 1)
        self.assertEqual(Payment.query.all()[0].transaction_id, 'TEST1')

        relatively_bad_form = good_form
        relatively_bad_form['txn_id'] = 'TEST2'
        relatively_bad_form['mc_gross'] = '0.49'
        Payment.process_paypal_ipn(relatively_bad_form)
        # There should still be one recorded donation
        self.assertEqual(len(Payment.query.all()), 1)

        bad_form = good_form
        relatively_bad_form['txn_id'] = 'TEST3'
        bad_form['business'] = current_app.config['PAYPAL_BUSINESS']
        Payment.process_paypal_ipn(bad_form)
        # There should still be one recorded donation
        self.assertEqual(len(Payment.query.all()), 1)

        super_bad_form = good_form
        relatively_bad_form['txn_id'] = 'TEST4'
        super_bad_form['payment_status'] = 'Refunded'  # What kind of monster would do that?!
        Payment.process_paypal_ipn(super_bad_form)
        # There should still be one recorded donation
        self.assertEqual(len(Payment.query.all()), 1)

    def test_verify_and_log_wepay_checkout_donation(self):
        checkout_id = 12345
        self.assertTrue(Payment.verify_and_log_wepay_checkout(
            checkout_id=12345,
            is_donation=True,
            editor='Tester',
            anonymous=False,
            can_contact=True,
        ))

        # Donation should be in the DB now
        self.assertEqual(Payment.query.all()[0].transaction_id, str(checkout_id))

    def test_verify_and_log_wepay_checkout_payment(self):
        checkout_id = 12345
        self.assertTrue(Payment.verify_and_log_wepay_checkout(
            checkout_id=12345,
            is_donation=False,
            invoice_number=42,
        ))

        # Donation should be in the DB now
        self.assertEqual(Payment.query.all()[0].transaction_id, str(checkout_id))

    def test_log_stripe_charge_donation(self):
        # Function should execute without any exceptions
        charge = convert_to_stripe_object(
            {
                "id": u"ch_15AjX1F21qH57QtHT6avvqrM",
                "object": u"charge",
                "created": 1418829367,
                "livemode": False,
                "paid": True,
                "status": u"succeeded",
                "amount": 99999900,
                "currency": u"usd",
                "refunded": False,
                "source": {
                    "id": u"card_15AjWxF21qH57QtHHVNgaHOP",
                    "object": u"card",
                    "last4": u"4242",
                    "brand": u"Visa",
                    "funding": u"credit",
                    "exp_month": 11,
                    "exp_year": 2016,
                    "country": u"US",
                    "name": u"Uh Oh",
                    "address_line1": u"test 12",
                    "address_line2": None,
                    "address_city": u"Schenectady",
                    "address_state": u"NY",
                    "address_zip": u"12345",
                    "address_country": u"United States",
                    "cvc_check": u"pass",
                    "address_line1_check": u"pass",
                    "address_zip_check": u"pass",
                    "dynamic_last4": None,
                    "metadata": {},
                    "customer": None
                },
                "captured": True,
                "balance_transaction": u"txn_159qthF21qH57QtHBksXX3tN",
                "failure_message": None,
                "failure_code": None,
                "amount_refunded": 0,
                "customer": None,
                "invoice": None,
                "description": u"Donation to MetaBrainz Foundation",
                "dispute": None,
                "metadata": {
                    "is_donation": True,
                    "anonymous": u"True",  # passed as a string
                    "can_contact": u"False",  # passed as a string
                    "email": u"mail@example.com",
                    "editor": u"null"
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

    def test_log_stripe_charge_payment(self):
        # Function should execute without any exceptions
        charge = convert_to_stripe_object(
            {
                "id": u"ch_15AjX1F21qH57QtHT6avvqrM",
                "object": u"charge",
                "created": 1418829367,
                "livemode": False,
                "paid": True,
                "status": u"succeeded",
                "amount": 99999900,
                "currency": u"usd",
                "refunded": False,
                "source": {
                    "id": u"card_15AjWxF21qH57QtHHVNgaHOP",
                    "object": u"card",
                    "last4": u"4242",
                    "brand": u"Visa",
                    "funding": u"credit",
                    "exp_month": 11,
                    "exp_year": 2016,
                    "country": u"US",
                    "name": u"Uh Oh",
                    "address_line1": u"test 12",
                    "address_line2": None,
                    "address_city": u"Schenectady",
                    "address_state": u"NY",
                    "address_zip": u"12345",
                    "address_country": u"United States",
                    "cvc_check": u"pass",
                    "address_line1_check": u"pass",
                    "address_zip_check": u"pass",
                    "dynamic_last4": None,
                    "metadata": {},
                    "customer": None
                },
                "captured": True,
                "balance_transaction": u"txn_159qthF21qH57QtHBksXX3tN",
                "failure_message": None,
                "failure_code": None,
                "amount_refunded": 0,
                "customer": None,
                "invoice": None,
                "description": u"Donation to MetaBrainz Foundation",
                "dispute": None,
                "metadata": {
                    "is_donation": False,
                    "email": u"mail@example.com",
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
