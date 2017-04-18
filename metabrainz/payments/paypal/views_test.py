# -*- coding: utf-8 -*-
from metabrainz.testing import FlaskTestCase
from metabrainz.model.payment import Payment
from flask import current_app, url_for
from metabrainz.payments.paypal import views


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

    def test_paypal_ipn_donation(self):
        ipn_data = {
            # This is not a complete list
            'first_name': u'Tester',
            'last_name': u'Testing',
            'custom': u'tester',  # MusicBrainz username
            'payer_email': u'test@example.org',
            'receiver_email': current_app.config['PAYPAL_ACCOUNT_IDS']['USD'],
            'business': u'donations@metabrainz.org',
            'address_street': u'1 Главная улица',
            'address_city': u'Сан Хозе',
            'address_state': u'CA',
            'address_country': u'США',
            'address_zip': u'95131',
            'mc_gross': u'42.50',
            'mc_fee': u'1',
            'txn_id': u'RANDOM-ID',
            'payment_status': u'Completed',

            # Additional variables:
            'option_name3': u'is_donation',
            'option_selection3': u'yes',
            'option_name1': u'anonymous',
            'option_selection1': u'yes',
            'option_name2': u'contact',
            'option_selection2': u'yes',
        }
        resp = self.client.post(
            url_for('payments_paypal.ipn'),
            headers=[('Content-Type', 'application/x-www-form-urlencoded')],
            data=ipn_data,
        )
        self.assert200(resp)

        # Donation should be in the DB now
        self.assertEqual(len(Payment.query.all()), 1)
        self.assertEqual(Payment.query.all()[0].transaction_id, u'RANDOM-ID')

    def test_paypal_ipn_payment(self):
        ipn_data = {
            # This is not a complete list
            'first_name': u'Tester',
            'last_name': u'Testing',
            'custom': u'tester',  # MusicBrainz username
            'payer_email': u'test@example.org',
            'receiver_email': current_app.config['PAYPAL_ACCOUNT_IDS']['USD'],
            'business': u'donations@metabrainz.org',
            'address_street': u'1 Главная улица',
            'address_city': u'Сан Хозе',
            'address_state': u'CA',
            'address_country': u'США',
            'address_zip': u'95131',
            'mc_gross': u'42.50',
            'mc_fee': u'1',
            'txn_id': u'RANDOM-ID',
            'payment_status': u'Completed',

            # Additional variables:
            'option_name3': u'is_donation',
            'option_selection3': u'no',
            'option_name4': u'invoice_number',
            'option_selection4': u'42',
        }
        resp = self.client.post(
            url_for('payments_paypal.ipn'),
            headers=[('Content-Type', 'application/x-www-form-urlencoded')],
            data=ipn_data,
        )
        self.assert200(resp)

        # Donation should be in the DB now
        self.assertEqual(len(Payment.query.all()), 1)
        self.assertEqual(Payment.query.all()[0].transaction_id, u'RANDOM-ID')

    def test_paypal_ipn_old(self):
        ipn_data = {
            # This is not a complete list
            'first_name': u'Tester',
            'last_name': u'Testing',
            'custom': u'tester',  # MusicBrainz username
            'payer_email': u'test@example.org',
            'receiver_email': current_app.config['PAYPAL_ACCOUNT_IDS']['USD'],
            'business': u'donations@metabrainz.org',
            'address_street': u'1 Главная улица',
            'address_city': u'Сан Хозе',
            'address_state': u'CA',
            'address_country': u'США',
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
            url_for('payments_paypal.ipn'),
            headers=[('Content-Type', 'application/x-www-form-urlencoded')],
            data=ipn_data,
        )
        self.assert200(resp)

        # Donation should be in the DB now
        self.assertEqual(len(Payment.query.all()), 1)
        self.assertEqual(Payment.query.all()[0].transaction_id, u'RANDOM-ID')

    def test_paypal_ipn_without_address(self):
        ipn_data = {
            # This is not a complete list
            'first_name': u'Tester',
            'last_name': u'Testing',
            'custom': u'tester',  # MusicBrainz username
            'payer_email': u'test@example.org',
            'receiver_email': current_app.config['PAYPAL_ACCOUNT_IDS']['USD'],
            'business': u'donations@metabrainz.org',
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
            url_for('payments_paypal.ipn'),
            headers=[('Content-Type', 'application/x-www-form-urlencoded')],
            data=ipn_data,
        )
        self.assert200(resp)

        # Donation should be in the DB now
        self.assertEqual(len(Payment.query.all()), 1)
        self.assertEqual(Payment.query.all()[0].transaction_id, u'RANDOM-ID')
