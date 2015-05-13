from metabrainz.testing import FlaskTestCase
from metabrainz.model.donation import Donation
from flask import current_app, url_for
from metabrainz.donations.paypal import views


class FakeResponse(object):
    """Fake response object for fake requests."""

    def __init__(self, text):
        self.text = text


class FakeRequests(object):
    def post(self, url, *args, **kwargs):
        """Always confirms verification as valid."""
        if url in ['https://www.paypal.com/cgi-bin/webscr',
                   'https://www.sandbox.paypal.com/cgi-bin/webscr']:
            return FakeResponse('VERIFIED')


class DonationsPayPalViewsTestCase(FlaskTestCase):
    def setUp(self):
        super(DonationsPayPalViewsTestCase, self).setUp()
        views.requests = FakeRequests()

    def test_paypal_ipn(self):
        ipn_data = {
            # This is not a complete list
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
            'txn_id': u'RANDOM-ID',
            'payment_status': u'Completed',

            # Additional variables:
            'option_name1': u'anonymous',
            'option_selection1': u'yes',
            'option_name2': u'contact',
            'option_selection2': u'yes',
        }
        resp = self.client.post(
            url_for('donations_paypal.ipn'),
            headers=[('Content-Type', 'application/x-www-form-urlencoded')],
            data=ipn_data,
        )
        self.assert200(resp)

        # Donation should be in the DB now
        self.assertEqual(len(Donation.query.all()), 1)
        self.assertEqual(Donation.query.all()[0].transaction_id, u'RANDOM-ID')
