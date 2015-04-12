from metabrainz.testing import FlaskTestCase
from flask import url_for


class DonationsViewsTestCase(FlaskTestCase):

    def test_index(self):
        self.assert200(self.client.get(url_for('donations.index')))

    def test_donors(self):
        response = self.client.get(url_for('donations.donors'))
        self.assert200(response)
