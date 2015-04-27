from metabrainz.testing import FlaskTestCase
from flask import url_for


class AdminViewsTestCase(FlaskTestCase):

    def test_index(self):
        self.assertStatus(self.client.get(url_for('admin.index')), 302)

    def test_usersview_index(self):
        self.assertStatus(self.client.get(url_for('usersview.index')), 302)

    def test_tokensview_index(self):
        self.assertStatus(self.client.get(url_for('tokensview.index')), 302)
