from metabrainz.testing import FlaskTestCase
from flask import url_for


class UsersViewsTestCase(FlaskTestCase):

    def test_customers_list(self):
        self.assert200(self.client.get(url_for('users.customers_list')))

    def test_tiers(self):
        self.assert200(self.client.get(url_for('users.tiers')))

    def test_bad(self):
        self.assert200(self.client.get(url_for('users.bad_standing')))
