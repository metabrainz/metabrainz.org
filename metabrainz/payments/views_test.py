from metabrainz.testing import FlaskTestCase
from metabrainz.model import db
from metabrainz.model.supporter import Supporter
from metabrainz.model.user import User
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
        user = User.add(
            name='test_user',
            unconfirmed_email='test@example.org',
            password='testing',
        )
        defaults = dict(
            is_commercial=True,
            contact_name='Test User',
            data_usage_desc='Testing',
            user=user,
        )
        defaults.update(kwargs)
        supporter = Supporter.add(**defaults)
        db.session.flush()
        return supporter

    def test_payment_selector_logged_in(self):
        supporter = self._create_supporter()
        self.temporary_login(supporter.user)
        self.assert200(self.client.get(url_for('payments.payment_selector')))

    def test_payment_logged_in(self):
        supporter = self._create_supporter(org_name='Test Org')
        self.temporary_login(supporter.user)
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
