from metabrainz.testing import FlaskTestCase
from metabrainz.model.donation import Donation
from flask import current_app, url_for
import views


class FakeResponse(object):
    """Fake response object for fake requests."""

    def __init__(self, text):
        self.text = text


class FakeRequests(object):
    def post(self, url, *args, **kwargs):
        if url in ['https://www.paypal.com/cgi-bin/webscr',
                   'https://www.sandbox.paypal.com/cgi-bin/webscr']:
            """Always confirms verification as valid."""
            return FakeResponse('VERIFIED')


class DonationsPayPalViewsTestCase(FlaskTestCase):
    def setUp(self):
        super(DonationsPayPalViewsTestCase, self).setUp()
        views.requests = FakeRequests()

    def test_paypal_ipn(self):
        ipn_data = {
            # This is not a complete list
            'first_name': 'Tester',
            'last_name': 'Testing',
            'custom': 'tester',  # MusicBrainz username
            'payer_email': 'test@example.org',
            'receiver_email': current_app.config['PAYPAL_PRIMARY_EMAIL'],
            'business': 'donations@metabrainz.org',
            'address_street': '1 Main St',
            'address_city': 'San Jose',
            'address_state': 'CA',
            'address_country': 'United States',
            'address_zip': '95131',
            'mc_gross': '42.50',
            'mc_fee': '1',
            'txn_id': 'RANDOM-ID',
            'payment_status': 'Completed',

            # Additional variables:
            'option_name1': 'anonymous',
            'option_selection1': 'yes',
            'option_name2': 'contact',
            'option_selection2': 'yes',
        }
        resp = self.client.post(url_for('donations_paypal.ipn'), data=ipn_data)
        self.assert200(resp)

        # Donation should be in the DB now
        self.assertEqual(len(Donation.query.all()), 1)
        self.assertEqual(Donation.query.all()[0].transaction_id, 'RANDOM-ID')
