# -*- coding: utf-8 -*-
from metabrainz.testing import FlaskTestCase
from metabrainz.model import donation
from metabrainz.model.donation import Donation
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
                'state': 'captured',
                'soft_descriptor': 'MetaBrainz Donation',
                'short_description': 'Donation to MetaBrainz Foundation',
                'currency': 'USD',
                'amount': 100,
                'fee': 3.2,
                'gross': 108.2,
                'app_fee': 5,
                'shipping_fee': 5,
                'fee_payer': 'payer',
                'reference_id': 'abc123',
                'redirect_uri': url_for(
                    'donations.complete',
                    _external=True,
                    _scheme=current_app.config['PREFERRED_URL_SCHEME'],
                ),
                'callback_uri': url_for(
                    'donations_wepay.ipn',
                    _scheme=current_app.config['PREFERRED_URL_SCHEME'],
                    _external=True,
                    editor='Tester',
                    anonymous=False,
                    can_contact=True,
                ),
                'payer_email': 'test@example.org',
                'payer_name': 'Tester Testing',
                'auto_capture': True,
            }
        else:
            raise NotImplementedError()


class DonationModelTestCase(FlaskTestCase):

    def setUp(self):
        super(DonationModelTestCase, self).setUp()
        donation.WePay = lambda production=True, access_token=None, api_version=None: \
            FakeWePay(production, access_token, api_version)

    def test_get_by_transaction_id(self):
        new = Donation()
        new.first_name = 'Tester'
        new.last_name = 'Testing'
        new.email = 'test@example.org'
        new.transaction_id = 'TEST'
        new.amount = 42.50
        db.session.add(new)
        db.session.commit()

        result = Donation.get_by_transaction_id('TEST')
        self.assertIsNotNone(result)

        bad_result = Donation.get_by_transaction_id('MISSING')
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
            'address_street': '1 Main St',
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
        Donation.process_paypal_ipn(good_form)
        # Donation should be in the DB now
        self.assertEqual(len(Donation.query.all()), 1)
        self.assertEqual(Donation.query.all()[0].transaction_id, 'TEST1')

        relatively_bad_form = good_form
        relatively_bad_form['txn_id'] = 'TEST2'
        relatively_bad_form['mc_gross'] = '0.49'
        Donation.process_paypal_ipn(relatively_bad_form)
        # There should still be one recorded donation
        self.assertEqual(len(Donation.query.all()), 1)

        bad_form = good_form
        relatively_bad_form['txn_id'] = 'TEST3'
        bad_form['business'] = current_app.config['PAYPAL_BUSINESS']
        Donation.process_paypal_ipn(bad_form)
        # There should still be one recorded donation
        self.assertEqual(len(Donation.query.all()), 1)

        super_bad_form = good_form
        relatively_bad_form['txn_id'] = 'TEST4'
        super_bad_form['payment_status'] = 'Refunded'  # What kind of monster would do that?!
        Donation.process_paypal_ipn(super_bad_form)
        # There should still be one recorded donation
        self.assertEqual(len(Donation.query.all()), 1)

    def test_verify_and_log_wepay_checkout(self):
        self.assertTrue(Donation.verify_and_log_wepay_checkout(12345, 'Tester', False, True))

        # Donation should be in the DB now
        self.assertEqual(Donation.query.all()[0].transaction_id, str(12345))

    def test_log_stripe_charge(self):
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
        Donation.log_stripe_charge(charge)
