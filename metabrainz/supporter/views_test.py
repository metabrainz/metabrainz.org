from urllib.parse import urlparse

from metabrainz import create_app
from metabrainz.testing import FlaskTestCase
from metabrainz.model.tier import Tier
from flask import url_for


class SupportersViewsTestCase(FlaskTestCase):

    def test_supporters_list(self):
        self.assert200(self.client.get(url_for('supporters.supporters_list')))

    def test_account_type(self):
        self.assert200(self.client.get(url_for('supporters.account_type')))

        Tier.create(
            name="Test tier",
            price=42,
            available=True,
            primary=False,
        )
        self.assert200(self.client.get(url_for('supporters.account_type')))

    def test_tier(self):
        t = Tier.create(
            name="Test tier",
            price=42,
            available=True,
            primary=False,
        )
        self.assert200(self.client.get(url_for('supporters.tier', tier_id=t.id)))
        self.assert404(self.client.get(url_for('supporters.tier', tier_id=t.id + 1)))

    def test_signup(self):
        self.assert200(self.client.get(url_for('users.signup')))

    def test_signup_commercial(self):
        resp = self.client.get(url_for('supporters.signup_commercial'))
        self.assertEqual(resp.location, urlparse(url_for('supporters.account_type')).path)

        unavailable_tier = Tier.create(
            name="Unavailable tier",
            price=42,
            available=False,
        )
        resp = self.client.get(url_for('supporters.signup_commercial', tier_id=unavailable_tier.id))
        self.assertEqual(resp.location, url_for('supporters.account_type'))

        resp = self.client.get(url_for('supporters.signup_commercial', tier_id='8"'))
        self.assertEqual(resp.location, url_for('supporters.account_type'))

        # With missing tier
        resp = self.client.get(url_for('supporters.signup_commercial', tier_id=unavailable_tier.id + 1))
        self.assertEqual(resp.location, url_for('supporters.account_type'))

    def test_musicbrainz(self):
        self.assertStatus(self.client.get(url_for('supporters.musicbrainz')), 302)

    def test_musicbrainz_post(self):
        app = create_app(debug=True, config_path='../config.py')
        app.config['TESTING'] = True
        client = app.test_client()

        self.assert500(client.get(url_for('supporters.musicbrainz_post')))
        self.assert400(client.get(url_for('supporters.musicbrainz_post', error="PANIC")))
        self.assert400(client.get(url_for('supporters.musicbrainz_post', state="fake")))

    def test_profile(self):
        self.assertStatus(self.client.get(url_for('supporters.profile')), 302)

    def test_profile_edit(self):
        self.assertStatus(self.client.get(url_for('supporters.profile_edit')), 302)

    def test_regenerate_token(self):
        self.assertStatus(self.client.post(url_for('supporters.regenerate_token')), 302)
        self.assertStatus(self.client.get(url_for('supporters.regenerate_token')), 405)

    def test_login(self):
        self.assert200(self.client.get(url_for('users.login')))

    def test_logout(self):
        self.assertStatus(self.client.get(url_for('users.logout')), 302)

    def test_bad_standing(self):
        self.assert200(self.client.get(url_for('supporters.bad_standing')))
