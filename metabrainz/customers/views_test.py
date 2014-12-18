from metabrainz.testing import FlaskTestCase
from flask import url_for


class CustomersViewsTestCase(FlaskTestCase):

    def test_index(self):
        self.assert200(self.client.get(url_for('customers.index')))

    def test_tiers(self):
        self.assert200(self.client.get(url_for('customers.tiers')))

    def test_bad(self):
        self.assert200(self.client.get(url_for('customers.bad_standing')))
