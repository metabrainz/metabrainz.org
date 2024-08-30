from metabrainz.testing import FlaskTestCase
from flask import url_for


class AdminViewsTestCase(FlaskTestCase):

    def test_index(self):
        self.assertStatus(self.client.get(url_for('admin.index')), 302)

    def test_supportersview_index(self):
        self.assertStatus(self.client.get(url_for('supportersview.index')), 302)

    def test_tokensview_index(self):
        self.assertStatus(self.client.get(url_for('tokensview.index')), 302)

    def test_statsview_index(self):
        self.assertStatus(self.client.get(url_for('statsview.overview')), 302)

    def test_statsview_top_ips(self):
        self.assertStatus(self.client.get(url_for('statsview.top_ips')), 302)

    def test_statsview_supporters(self):
        self.assertStatus(self.client.get(url_for('statsview.supporters')), 302)
