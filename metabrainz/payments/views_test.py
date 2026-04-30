from metabrainz.testing import FlaskTestCase
from metabrainz.model.supporter import Supporter
from flask import url_for


class PaymentsViewsTestCase(FlaskTestCase):

    def test_donate(self):
        self.assert200(self.client.get(url_for('payments.donate')))

    def test_payment_selector_is_public(self):
        self.assert200(self.client.get(url_for('payments.payment_selector')))

    def test_payment_is_public(self):
        resp = self.client.get(url_for('payments.payment', currency='usd'))
        self.assert200(resp)
        self.assertNotIn(b'Organization:', resp.data)
        self.assertNotIn(b'Supporter level:', resp.data)

    def _create_supporter(self, **kwargs):
        defaults = dict(
            is_commercial=True,
            musicbrainz_id='test_user',
            musicbrainz_row_id=1,
            contact_name='Test User',
            contact_email='test@example.org',
            data_usage_desc='Testing',
        )
        defaults.update(kwargs)
        return Supporter.add(**defaults)

    def test_payment_selector_logged_in(self):
        supporter = self._create_supporter()
        self.temporary_login(supporter.id)
        self.assert200(self.client.get(url_for('payments.payment_selector')))

    def test_payment_logged_in(self):
        supporter = self._create_supporter(org_name='Test Org')
        self.temporary_login(supporter.id)
        resp = self.client.get(url_for('payments.payment', currency='usd'))
        self.assert200(resp)
        self.assertIn(b'Organization:', resp.data)
        self.assertIn(b'Test Org', resp.data)
        self.assert200(self.client.get(url_for('payments.payment', currency='eur')))

    def test_cancel_recurring(self):
        self.assert200(self.client.get(url_for('payments.cancel_recurring')))

    def test_donors(self):
        response = self.client.get(url_for('payments.donors'))
        self.assert200(response)
