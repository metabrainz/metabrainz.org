from metabrainz.testing import FlaskTestCase
from metabrainz.model.tier import Tier
from flask import url_for


class UsersViewsTestCase(FlaskTestCase):

    def test_supporters_list(self):
        self.assert200(self.client.get(url_for('users.supporters_list')))

    def test_tiers(self):
        self.assert200(self.client.get(url_for('users.tiers')))

        Tier.create(
            name="Test tier",
            price=42,
            available=True,
            primary=False,
        )
        self.assert200(self.client.get(url_for('users.tiers')))

    def test_tier(self):
        t = Tier.create(
            name="Test tier",
            price=42,
            available=True,
            primary=False,
        )
        self.assert200(self.client.get(url_for('users.tier', tier_id=t.id)))
        self.assert404(self.client.get(url_for('users.tier', tier_id=t.id + 1)))

    def test_signup(self):
        self.assert200(self.client.get(url_for('users.signup')))

    def test_signup_tier_selection(self):
        self.assert200(self.client.get(url_for('users.signup_tier_selection')))

    def test_signup_commercial(self):
        resp = self.client.get(url_for('users.signup_commercial'))
        self.assertRedirects(resp, url_for('users.signup_tier_selection'))

        unavailable_tier = Tier.create(
            name="Unavailable tier",
            price=42,
            available=False,
        )
        resp = self.client.get(url_for('users.signup_commercial', tier_id=unavailable_tier.id))
        self.assertRedirects(resp, url_for('users.signup_tier_selection'))

        # With missing tier
        resp = self.client.get(url_for('users.signup_commercial', tier_id=unavailable_tier.id + 1))
        self.assertRedirects(resp, url_for('users.signup_tier_selection'))

        available_tier = Tier.create(
            name="Available tier",
            price=42,
            available=True,
        )
        self.assert200(self.client.get(url_for('users.signup_commercial', tier_id=available_tier.id)))

    def test_signup_non_commercial(self):
        self.assert200(self.client.get(url_for('users.signup_non_commercial')))

    def test_musicbrainz(self):
        self.assertStatus(self.client.get(url_for('users.musicbrainz')), 302)

    def test_musicbrainz_post(self):
        self.assert500(self.client.get(url_for('users.musicbrainz_post')))
        self.assert400(self.client.get(url_for('users.musicbrainz_post', error="PANIC")))
        self.assert400(self.client.get(url_for('users.musicbrainz_post', state="fake")))

    def test_profile(self):
        self.assertStatus(self.client.get(url_for('users.profile')), 302)

    def test_profile_edit(self):
        self.assertStatus(self.client.get(url_for('users.profile_edit')), 302)

    def test_regenerate_token(self):
        self.assertStatus(self.client.post(url_for('users.regenerate_token')), 302)
        self.assert405(self.client.get(url_for('users.regenerate_token')))

    def test_login(self):
        self.assert200(self.client.get(url_for('users.login')))

    def test_logout(self):
        self.assertStatus(self.client.get(url_for('users.logout')), 302)

    def test_bad_standing(self):
        self.assert200(self.client.get(url_for('users.bad_standing')))
