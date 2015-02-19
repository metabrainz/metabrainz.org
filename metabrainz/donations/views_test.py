from metabrainz.testing import FlaskTestCase
from flask import url_for


class DonationsViewsTestCase(FlaskTestCase):

    def test_index(self):
        self.assert200(self.client.get(url_for('donations.index')))

    def test_donors(self):
        response = self.client.get(url_for('donations.donors'))
        self.assert200(response)

    def test_complete(self):
        response = self.client.get(url_for('donations.complete'))
        self.assertStatus(response, 302)
        response = self.client.post(url_for('donations.complete'))
        self.assertStatus(response, 302)

    def test_cancelled(self):
        response = self.client.get(url_for('donations.cancelled'))
        self.assertStatus(response, 302)

    def test_error(self):
        response = self.client.get(url_for('donations.error'))
        self.assertStatus(response, 302)
