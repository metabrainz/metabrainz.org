from metabrainz.testing import FlaskTestCase
from metabrainz.model.supporter import Supporter
from flask import url_for


class AdminViewsTestCase(FlaskTestCase):

    def _login_admin(self):
        supporter = Supporter.add(
            is_commercial=False,
            musicbrainz_id='admin_user',
            musicbrainz_row_id=1,
            contact_name='Admin',
            contact_email='admin@example.com',
            data_usage_desc='testing',
        )
        self.app.config['ADMINS'] = ['admin_user']
        self.temporary_login(supporter.id)

    def test_index_unauthenticated(self):
        self.assertStatus(self.client.get(url_for('admin.index')), 302)

    def test_index_as_admin(self):
        self._login_admin()
        self.assert200(self.client.get(url_for('admin.index')))

    def test_supportersview_index_unauthenticated(self):
        self.assertStatus(self.client.get(url_for('supportersview.index')), 302)

    def test_supportersview_index_as_admin(self):
        self._login_admin()
        self.assert200(self.client.get(url_for('supportersview.index')))

    def test_tokensview_index_unauthenticated(self):
        self.assertStatus(self.client.get(url_for('tokensview.index')), 302)

    def test_tokensview_index_as_admin(self):
        self._login_admin()
        self.assert200(self.client.get(url_for('tokensview.index')))

    def test_statsview_index_unauthenticated(self):
        self.assertStatus(self.client.get(url_for('statsview.overview')), 302)

    def test_statsview_index_as_admin(self):
        self._login_admin()
        self.assert200(self.client.get(url_for('statsview.overview')))

    def test_statsview_top_ips_unauthenticated(self):
        self.assertStatus(self.client.get(url_for('statsview.top_ips')), 302)

    def test_statsview_top_ips_as_admin(self):
        self._login_admin()
        self.assert200(self.client.get(url_for('statsview.top_ips')))

    def test_statsview_supporters_unauthenticated(self):
        self.assertStatus(self.client.get(url_for('statsview.supporters')), 302)

    def test_statsview_supporters_as_admin(self):
        self._login_admin()
        self.assert200(self.client.get(url_for('statsview.supporters')))

    def test_commercialsupportersview_index_unauthenticated(self):
        self.assertStatus(self.client.get(url_for('commercialsupportersview.index')), 302)

    def test_commercialsupportersview_index_as_admin(self):
        self._login_admin()
        self.assert200(self.client.get(url_for('commercialsupportersview.index')))
