import json
from urllib.parse import urlparse

from brainzutils import cache
from flask import url_for, g
from flask_login import current_user
from sqlalchemy import delete

from metabrainz.model import db
from metabrainz.model.dataset import Dataset
from metabrainz.model.supporter import Supporter
from metabrainz.model.tier import Tier
from metabrainz.model.user import User
from metabrainz.testing import FlaskTestCase


class SupportersViewsTestCase(FlaskTestCase):

    def setUp(self):
        super().setUp()
        self.existing_user = User(name="existing-test-user", password="testpassword123")
        db.session.add(self.existing_user)
        db.session.commit()

        self.tier = Tier.create(
            name="Test Tier",
            price=100,
            available=True,
            primary=False,
        )

        self.dataset = Dataset.create(
            name="Test Dataset",
            description="A test dataset",
            project="musicbrainz"
        )
        self.app.config["SIGNUP_RATE_LIMIT_PER_IP"] = 2
        self.ip_address = "10.0.0.100"

    def tearDown(self):
        db.session.rollback()
        db.session.execute(delete(Supporter))
        db.session.execute(delete(User))
        db.session.execute(delete(Tier))
        db.session.execute(delete(Dataset))
        db.session.commit()
        cache._r.flushall()
        super().tearDown()

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

    def test_profile(self):
        self.assertStatus(self.client.get(url_for('index.profile')), 302)

    def test_profile_edit(self):
        self.assertStatus(self.client.get(url_for('index.profile_edit')), 302)

    def test_regenerate_token(self):
        self.assertStatus(self.client.post(url_for('supporters.regenerate_token')), 302)
        self.assertStatus(self.client.get(url_for('supporters.regenerate_token')), 405)

    def test_bad_standing(self):
        self.assert200(self.client.get(url_for('supporters.bad_standing')))

    def test_become_commercial_supporter_success(self):
        self.temporary_login(self.existing_user)

        response = self.client.get(
            url_for('supporters.signup_commercial', tier_id=self.tier.id)
        )
        self.assert200(response)
        self.assertTemplateUsed("supporters/signup-commercial.html")

        props = json.loads(self.get_context_variable("props"))
        self.assertTrue(props["existing_user"])
        self.assertEqual(props["user"]["username"], "existing-test-user")
        self.assertEqual(props["tier"]["name"], "Test Tier")
        self.assertEqual(props["tier"]["price"], 100.0)

        response = self.client.post(
            url_for('supporters.signup_commercial', tier_id=self.tier.id),
            data={
                "contact_name": "Test Contact",
                "usage_desc": "Testing the API for my project",
                "org_name": "Test Organization",
                "org_desc": "A test organization description",
                "website_url": "https://example.com",
                "logo_url": "https://example.com/logo.png",
                "api_url": "https://api.example.com",
                "address_street": "123 Test St",
                "address_city": "Test City",
                "address_state": "Test State",
                "address_postcode": "12345",
                "address_country": "Test Country",
                "amount_pledged": "150",
                "agreement": "y",
                "mtcaptcha": "test-token",
                "csrf_token": g.csrf_token,
            },
            follow_redirects=False
        )
        self.assertRedirects(response, url_for('index.profile'))

        supporter = Supporter.query.filter_by(user_id=self.existing_user.id).first()
        self.assertIsNotNone(supporter)
        self.assertTrue(supporter.is_commercial)
        self.assertEqual(supporter.org_name, "Test Organization")
        self.assertEqual(supporter.contact_name, "Test Contact")
        self.assertEqual(float(supporter.amount_pledged), 150.0)

    def test_become_commercial_supporter_amount_pledged_validation(self):
        self.temporary_login(self.existing_user)

        self.client.get(url_for('supporters.signup_commercial', tier_id=self.tier.id))

        response = self.client.post(
            url_for('supporters.signup_commercial', tier_id=self.tier.id),
            data={
                "contact_name": "Test Contact",
                "usage_desc": "Testing the API for my project",
                "org_name": "Test Organization",
                "org_desc": "A test organization description",
                "website_url": "https://example.com",
                "address_street": "123 Test St",
                "address_city": "Test City",
                "address_state": "Test State",
                "address_postcode": "12345",
                "address_country": "Test Country",
                "amount_pledged": "50",
                "agreement": "y",
                "mtcaptcha": "test-token",
                "csrf_token": g.csrf_token,
            }
        )
        self.assert200(response)

        props = json.loads(self.get_context_variable("props"))
        self.assertIn("amount_pledged", props["initial_errors"])

        supporter = Supporter.query.filter_by(user_id=self.existing_user.id).first()
        self.assertIsNone(supporter)

    def test_become_noncommercial_supporter_success(self):
        self.temporary_login(self.existing_user)

        response = self.client.get(url_for('supporters.signup_noncommercial'))
        self.assert200(response)
        self.assertTemplateUsed("supporters/signup-non-commercial.html")

        props = json.loads(self.get_context_variable("props"))
        self.assertTrue(props["existing_user"])
        self.assertEqual(props["user"]["username"], "existing-test-user")
        self.assertEqual(len(props["datasets"]), 1)
        self.assertEqual(props["datasets"][0]["name"], "Test Dataset")

        response = self.client.post(
            url_for('supporters.signup_noncommercial'),
            data={
                "contact_name": "Test Contact",
                "usage_desc": "Personal project using the data",
                f"datasets.{self.dataset.id}": "y",
                "agreement": "y",
                "mtcaptcha": "test-token",
                "csrf_token": g.csrf_token,
            },
            follow_redirects=False
        )

        self.assertRedirects(response, url_for('index.profile'))

        supporter = Supporter.query.filter_by(user_id=self.existing_user.id).first()
        self.assertIsNotNone(supporter)
        self.assertFalse(supporter.is_commercial)
        self.assertEqual(supporter.contact_name, "Test Contact")
        self.assertEqual(supporter.data_usage_desc, "Personal project using the data")

    def test_already_supporter_redirects(self):
        self.temporary_login(self.existing_user)
        Supporter.add(
            is_commercial=False,
            contact_name="Test",
            data_usage_desc="Test",
            datasets=[],
            user=self.existing_user
        )
        db.session.commit()

        response = self.client.get(
            url_for('supporters.signup_commercial', tier_id=self.tier.id),
            follow_redirects=False
        )
        self.assertRedirects(response, url_for('index.profile'))

        response = self.client.get(
            url_for('supporters.signup_noncommercial'),
            follow_redirects=False
        )
        self.assertRedirects(response, url_for('index.profile'))

    def test_become_commercial_supporter_missing_required_fields(self):
        self.temporary_login(self.existing_user)

        self.client.get(url_for('supporters.signup_commercial', tier_id=self.tier.id))
        response = self.client.post(
            url_for('supporters.signup_commercial', tier_id=self.tier.id),
            data={
                "csrf_token": g.csrf_token,
                "mtcaptcha": "test-token",
            }
        )

        self.assert200(response)
        props = json.loads(self.get_context_variable("props"))

        self.assertIn("contact_name", props["initial_errors"])
        self.assertIn("org_name", props["initial_errors"])
        self.assertIn("website_url", props["initial_errors"])

    def test_become_noncommercial_supporter_missing_required_fields(self):
        self.temporary_login(self.existing_user)

        self.client.get(url_for('supporters.signup_noncommercial'))

        response = self.client.post(
            url_for('supporters.signup_noncommercial'),
            data={
                "csrf_token": g.csrf_token,
                "mtcaptcha": "test-token",
            }
        )
        self.assert200(response)
        props = json.loads(self.get_context_variable("props"))

        self.assertIn("contact_name", props["initial_errors"])
        self.assertIn("usage_desc", props["initial_errors"])

    def test_signup_commercial_success_new_user(self):
        response = self.client.get(
            url_for('supporters.signup_commercial', tier_id=self.tier.id)
        )
        self.assert200(response)
        self.assertTemplateUsed("supporters/signup-commercial.html")

        props = json.loads(self.get_context_variable("props"))
        self.assertFalse(props["existing_user"])
        self.assertNotIn("user", props)
        self.assertEqual(props["tier"]["name"], "Test Tier")
        self.assertEqual(props["tier"]["price"], 100.0)

        response = self.client.post(
            url_for('supporters.signup_commercial', tier_id=self.tier.id),
            data={
                "username": "new_commercial_user",
                "email": "commercial@example.com",
                "password": "securepassword123",
                "confirm_password": "securepassword123",
                "contact_name": "New Commercial Contact",
                "usage_desc": "Building a commercial music app",
                "org_name": "New Commercial Org",
                "org_desc": "A new commercial organization",
                "website_url": "https://newcommercial.example.com",
                "logo_url": "https://newcommercial.example.com/logo.png",
                "api_url": "https://api.newcommercial.example.com",
                "address_street": "456 Commercial St",
                "address_city": "Commerce City",
                "address_state": "Commerce State",
                "address_postcode": "67890",
                "address_country": "Commerce Country",
                "amount_pledged": "200",
                "agreement": "y",
                "mtcaptcha": "test-token",
                "csrf_token": g.csrf_token,
            },
            follow_redirects=False
        )

        self.assertRedirects(response, url_for("index.profile"))

        user = User.get(name="new_commercial_user")
        self.assertIsNotNone(user)
        self.assertEqual(user.unconfirmed_email, "commercial@example.com")

        supporter = Supporter.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(supporter)
        self.assertTrue(supporter.is_commercial)
        self.assertEqual(supporter.org_name, "New Commercial Org")
        self.assertEqual(supporter.contact_name, "New Commercial Contact")
        self.assertEqual(float(supporter.amount_pledged), 200.0)

    def test_signup_commercial_duplicate_username(self):
        self.client.get(url_for('supporters.signup_commercial', tier_id=self.tier.id))

        response = self.client.post(
            url_for('supporters.signup_commercial', tier_id=self.tier.id),
            data={
                "username": "existing-test-user",
                "email": "newemail@example.com",
                "password": "securepassword123",
                "confirm_password": "securepassword123",
                "contact_name": "Test Contact",
                "usage_desc": "Testing",
                "org_name": "Test Org",
                "org_desc": "Test description",
                "website_url": "https://example.com",
                "address_street": "123 Test St",
                "address_city": "Test City",
                "address_state": "Test State",
                "address_postcode": "12345",
                "address_country": "Test Country",
                "amount_pledged": "150",
                "agreement": "y",
                "mtcaptcha": "test-token",
                "csrf_token": g.csrf_token,
            }
        )

        self.assert200(response)
        props = json.loads(self.get_context_variable("props"))
        self.assertIn("username", props["initial_errors"])

    def test_signup_commercial_missing_user_fields(self):
        self.client.get(url_for('supporters.signup_commercial', tier_id=self.tier.id))

        response = self.client.post(
            url_for('supporters.signup_commercial', tier_id=self.tier.id),
            data={
                # Missing username, email, password fields
                "contact_name": "Test Contact",
                "usage_desc": "Testing",
                "org_name": "Test Org",
                "org_desc": "Test description",
                "website_url": "https://example.com",
                "address_street": "123 Test St",
                "address_city": "Test City",
                "address_state": "Test State",
                "address_postcode": "12345",
                "address_country": "Test Country",
                "amount_pledged": "150",
                "agreement": "y",
                "mtcaptcha": "test-token",
                "csrf_token": g.csrf_token,
            }
        )

        self.assert200(response)
        props = json.loads(self.get_context_variable("props"))
        self.assertIn("username", props["initial_errors"])
        self.assertIn("email", props["initial_errors"])
        self.assertIn("password", props["initial_errors"])

    def test_signup_noncommercial_new_user(self):
        response = self.client.get(url_for('supporters.signup_noncommercial'))
        self.assert200(response)
        self.assertTemplateUsed("supporters/signup-non-commercial.html")

        props = json.loads(self.get_context_variable("props"))
        self.assertFalse(props["existing_user"])
        self.assertNotIn("user", props)
        self.assertEqual(len(props["datasets"]), 1)
        self.assertEqual(props["datasets"][0]["name"], "Test Dataset")

        response = self.client.post(
            url_for('supporters.signup_noncommercial'),
            data={
                "username": "new_noncommercial_user",
                "email": "noncommercial@example.com",
                "password": "securepassword123",
                "confirm_password": "securepassword123",
                "contact_name": "New NonCommercial Contact",
                "usage_desc": "Personal hobby project",
                f"datasets.{self.dataset.id}": "y",
                "agreement": "y",
                "mtcaptcha": "test-token",
                "csrf_token": g.csrf_token,
            },
            follow_redirects=False
        )

        self.assertRedirects(response, url_for('index.profile'))

        user = User.get(name="new_noncommercial_user")
        self.assertIsNotNone(user)
        self.assertEqual(user.unconfirmed_email, "noncommercial@example.com")

        supporter = Supporter.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(supporter)
        self.assertFalse(supporter.is_commercial)
        self.assertEqual(supporter.contact_name, "New NonCommercial Contact")
        self.assertEqual(supporter.data_usage_desc, "Personal hobby project")

    def test_signup_noncommercial_duplicate_username(self):
        self.client.get(url_for('supporters.signup_noncommercial'))

        response = self.client.post(
            url_for('supporters.signup_noncommercial'),
            data={
                "username": "existing-test-user",  # Already exists
                "email": "newemail@example.com",
                "password": "securepassword123",
                "confirm_password": "securepassword123",
                "contact_name": "Test Contact",
                "usage_desc": "Testing",
                f"datasets.{self.dataset.id}": "y",
                "agreement": "y",
                "mtcaptcha": "test-token",
                "csrf_token": g.csrf_token,
            }
        )

        self.assert200(response)
        props = json.loads(self.get_context_variable("props"))
        self.assertIn("username", props["initial_errors"])

    def test_signup_noncommercial_duplicate_email(self):
        self.existing_user.email = "existing@example.com"
        db.session.commit()

        self.client.get(url_for('supporters.signup_noncommercial'))

        response = self.client.post(
            url_for('supporters.signup_noncommercial'),
            data={
                "username": "brand_new_user",
                "email": "existing@example.com",  # Already exists
                "password": "securepassword123",
                "confirm_password": "securepassword123",
                "contact_name": "Test Contact",
                "usage_desc": "Testing",
                f"datasets.{self.dataset.id}": "y",
                "agreement": "y",
                "mtcaptcha": "test-token",
                "csrf_token": g.csrf_token,
            }
        )

        self.assert200(response)
        props = json.loads(self.get_context_variable("props"))
        self.assertIn("email", props["initial_errors"])

    def test_signup_noncommercial_missing_user_fields(self):
        self.client.get(url_for('supporters.signup_noncommercial'))

        response = self.client.post(
            url_for('supporters.signup_noncommercial'),
            data={
                # Missing username, email, password fields
                "contact_name": "Test Contact",
                "usage_desc": "Testing",
                f"datasets.{self.dataset.id}": "y",
                "agreement": "y",
                "mtcaptcha": "test-token",
                "csrf_token": g.csrf_token,
            }
        )

        self.assert200(response)
        props = json.loads(self.get_context_variable("props"))
        self.assertIn("username", props["initial_errors"])
        self.assertIn("email", props["initial_errors"])
        self.assertIn("password", props["initial_errors"])

    def test_signup_noncommercial_password_mismatch(self):
        self.client.get(url_for('supporters.signup_noncommercial'))

        response = self.client.post(
            url_for('supporters.signup_noncommercial'),
            data={
                "username": "new_user",
                "email": "new@example.com",
                "password": "securepassword123",
                "confirm_password": "differentpassword",  # Doesn't match
                "contact_name": "Test Contact",
                "usage_desc": "Testing",
                f"datasets.{self.dataset.id}": "y",
                "agreement": "y",
                "mtcaptcha": "test-token",
                "csrf_token": g.csrf_token,
            }
        )

        self.assert200(response)
        props = json.loads(self.get_context_variable("props"))
        self.assertIn("confirm_password", props["initial_errors"])

    def _signup_with_ip(self, is_commercial: bool, username: str | None, email: str | None, ip_address: str = None):
        """Helper to perform commercial signup with a specific IP address."""
        data = {
            "username": username,
            "email": email,
            "password": "securepassword123",
            "confirm_password": "securepassword123",
            "contact_name": "Test Contact",
            "usage_desc": "Testing",
            "agreement": "y",
        }
        if is_commercial:
            url = url_for('supporters.signup_commercial', tier_id=self.tier.id)
            data.update({
                "org_name": "Test Org 1",
                "org_desc": "Test description",
                "website_url": "https://example1.com",
                "address_street": "123 Test St",
                "address_city": "Test City",
                "address_state": "Test State",
                "address_postcode": "12345",
                "address_country": "Test Country",
                "amount_pledged": "150",
            })
        else:
            url = url_for("supporters.signup_noncommercial")
            data[f"datasets.{self.dataset.id}"] = "y"

        env = {"REMOTE_ADDR": ip_address or self.ip_address}
        self.client.get(url, environ_base=env)
        data["csrf_token"] = g.csrf_token
        return self.client.post(url, data=data, environ_base=env)

    def _test_signup_rate_limit(self, is_commercial: bool):
        # test failed validation doesn't increase signup count
        for _ in range(5):
            response = self._signup_with_ip(
                is_commercial=is_commercial,
                username=None,
                email="test@email.com"
            )
            self.assert200(response)
            props = json.loads(self.get_context_variable("props"))
            self.assertIn("username", props["initial_errors"])
            self.assertIn("Username is required!", props["initial_errors"]["username"])

        response = self._signup_with_ip(
            is_commercial=is_commercial,
            username="new_user_1",
            email="new_user_1@example.com"
        )
        self.assertRedirects(response, url_for("index.profile"))
        self.client.get("/logout")
        response = self._signup_with_ip(
            is_commercial=is_commercial,
            username="new_user_2",
            email="new_user_2@example.com"
        )
        self.assertRedirects(response, url_for("index.profile"))
        self.client.get("/logout")

        response = self._signup_with_ip(
            is_commercial=is_commercial,
            username="new_user_3",
            email="new_user_3@example.com"
        )
        self.assert200(response)
        props = json.loads(self.get_context_variable("props"))
        self.assertIn("null", props["initial_errors"])
        self.assertIn("Too many registration attempts", props["initial_errors"]["null"])

        user = User.get(name="new_user_3")
        self.assertIsNone(user)

        # existing user becoming supporter is not rate-limited
        self.temporary_login(self.existing_user)
        response = self._signup_with_ip(
            is_commercial=is_commercial,
            username=self.existing_user.name,
            email=self.existing_user.email
        )
        self.assertRedirects(response, url_for("index.profile"))
        self.assertIsNotNone(current_user.supporter)

    def test_signup_commercial_rate_limit(self):
        self._test_signup_rate_limit(is_commercial=True)

    def test_signup_noncommercial_rate_limit(self):
        self._test_signup_rate_limit(is_commercial=False)
