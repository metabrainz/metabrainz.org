from metabrainz.testing import FlaskTestCase
import donation
from donation import Donation
from metabrainz.model import db
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
                'redirect_uri': url_for('donations.complete', _external=True),
                'callback_uri': url_for('donations.wepay_ipn', _external=True,
                                        editor='Tester',
                                        anonymous=False,
                                        can_contact=True),
                'payer_email': 'api@wepay.com',
                'payer_name': 'Tester Testing',
                'auto_capture': True,
            }
        else:
            raise NotImplementedError()


class DonationModelTestCase(FlaskTestCase):

    def setUp(self):
        super(DonationModelTestCase, self).setUp()
        donation.WePay = lambda production=True, access_token=None, api_version=None:\
            FakeWePay(production, access_token, api_version)

    def test_get_by_transaction_id(self):
        new = Donation()
        new.first_name = 'Tester'
        new.last_name = 'Testing'
        new.email = 'testing@testers.org'
        new.transaction_id = 'TEST'
        new.amount = 42.50
        db.session.add(new)
        db.session.commit()

        result = Donation.get_by_transaction_id('TEST')
        self.assertIsNotNone(result)

        bad_result = Donation.get_by_transaction_id('MISSING')
        self.assertIsNone(bad_result)

    def test_process_paypal_ipn(self):
        good_form = {  # This is not a complete list
            'first_name': 'Tester',
            'last_name': 'Testing',
            'custom': 'tester',  # MusicBrainz username
            'payer_email': 'tester@metabrainz.org',  # MusicBrainz username
            'receiver_email': current_app.config['PAYPAL_PRIMARY_EMAIL'],
            'business': 'donations@metabrainz.org',
            'address_street': '1 Main St',
            'address_city': 'San Jose',
            'address_state': 'CA',
            'address_country': 'United States',
            'address_zip': '95131',
            'mc_gross': '42.50',
            'mc_fee': '1',
            'txn_id': 'TEST1',
            'payment_status': 'Completed',

            # Additional variables:
            'option_name1': 'anonymous',
            'option_selection1': 'yes',
            'option_name2': 'contact',
            'option_selection2': 'yes',
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
