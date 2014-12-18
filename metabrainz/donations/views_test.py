from metabrainz.testing import FlaskTestCase
from flask import url_for


class DonationsViewsTestCase(FlaskTestCase):

    def test_index(self):
        self.assert200(self.client.get(url_for('donations.index')))

    def test_donors(self):
        response = self.client.get(url_for('donations.donors'))
        self.assert200(response)

    def test_complete(self):
        self.assert200(self.client.get(url_for('donations.complete')))
        self.assert200(self.client.post(url_for('donations.complete')))

    def test_cancelled(self):
        self.assert200(self.client.get(url_for('donations.cancelled')))

    def test_error(self):
        self.assert200(self.client.get(url_for('donations.error')))
