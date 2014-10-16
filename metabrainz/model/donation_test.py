from metabrainz.model.testing import ModelTestCase
import donation
from donation import Donation
from metabrainz.model import db
from flask import url_for


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
                'redirect_uri': url_for('donation.complete', _external=True),
                'callback_uri': url_for('donation.wepay_ipn', _external=True,
                                        editor='Tester',
                                        anonymous=False,
                                        can_contact=True),
                'payer_email': 'api@wepay.com',
                'payer_name': 'Tester Testing',
                'auto_capture': True,
            }
        else:
            raise NotImplementedError()


class DonationModelTestCase(ModelTestCase):
    def setUp(self):
        super(DonationModelTestCase, self).setUp()
        donation.WePay = lambda production=True, access_token=None, api_version=None: FakeWePay(production, access_token, api_version)

    def test_addition(self):
        new = Donation()
        new.first_name = 'Tester'
        new.last_name = 'Testing'
        new.email = 'testing@testers.org'
        new.transaction_id = 'TEST'
        new.amount = 42.50
        db.session.add(new)
        db.session.commit()

        donations = Donation.query.all()
        self.assertEqual(len(donations), 1)

    def test_verify_and_log_wepay_checkout(self):
        self.assertTrue(Donation.verify_and_log_wepay_checkout(12345, 'Tester', False, True))

        # Donation should be in the DB now
        donation = Donation.query.all()[0]
        self.assertEqual(donation.transaction_id, str(12345))
