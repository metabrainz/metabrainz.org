import json
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs

from flask import g, url_for
from flask_login import current_user
from flask_wtf.csrf import generate_csrf
from freezegun import freeze_time
from sqlalchemy import delete

from metabrainz.model import db
from metabrainz.model.old_username import OldUsername
from metabrainz.model.user import User
from metabrainz.testing import FlaskTestCase
from metabrainz.user.email import VERIFY_EMAIL, create_email_link_checksum, RESET_PASSWORD


class UsersViewsTestCase(FlaskTestCase):

    def setUp(self):
        super(UsersViewsTestCase, self).setUp()

    def tearDown(self):
        db.session.rollback()
        db.session.execute(delete(User))
        db.session.execute(delete(OldUsername))
        db.session.commit()
        super(UsersViewsTestCase, self).tearDown()

    def create_user(self, data=None):
        if data is None:
            data = {
                "username": "test_user_1",
                "email": "test@example.com",
                "password": "<PASSWORD>",
                "confirm_password": "<PASSWORD>",
            }
        self._test_user_signup_helper(data, 302)
        self.client.get("/logout")

    def _test_user_signup_helper(self, data, expected_status_code, include_csrf_token=True):
        self.client.get("/signup")
        if include_csrf_token:
            data["csrf_token"] = g.csrf_token
        response = self.client.post("/signup", data=data)
        self.assertEqual(response.status_code, expected_status_code)

    def _test_user_signup_missing_fields_helper(self, data, errors, include_csrf_token=True):
        self._test_user_signup_helper(data, 200, include_csrf_token)
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["initial_errors"], errors)
        user = User.get(name="test_user_1")
        self.assertIsNone(user)

    def test_user_signup_success(self):
        self._test_user_signup_helper({
            "username": "test_user_1",
            "email": "test@example.com",
            "password": "<PASSWORD>",
            "confirm_password": "<PASSWORD>",
        }, 302)
        self.assertMessageFlashed("Account created. Please check your inbox to complete verification.", "success")

        user = User.get(name="test_user_1")
        self.assertEqual(user.name, "test_user_1")
        self.assertIsNone(user.email)
        self.assertEqual(user.unconfirmed_email, "test@example.com")
        self.assertIsNone(user.email_confirmed_at)
        self.assertNotEqual(user.password, "<PASSWORD>")
        self.assertIsNotNone(user.member_since)
        self.assertIsNotNone(user.last_login_at)
        self.assertIsNotNone(user.last_updated)
        self.assertEqual(current_user, user)

    def test_user_signup_missing_csrf_token(self):
        self._test_user_signup_missing_fields_helper({
            "username": "test_user_1",
            "email": "test@example.com",
            "password": "<PASSWORD>",
            "confirm_password": "<PASSWORD>",
        }, {"csrf_token": "The CSRF token is missing."}, False)
        user = User.get(name="test_user_1")
        self.assertIsNone(user)

    def test_user_signup_missing_username(self):
        self._test_user_signup_missing_fields_helper({
            "email": "test@example.com",
            "password": "<PASSWORD>",
            "confirm_password": "<PASSWORD>",
        }, {"username": "Username is required!"})
        user = User.get(email="test@example.com")
        self.assertIsNone(user)

    def test_user_signup_missing_email(self):
        self._test_user_signup_missing_fields_helper({
            "username": "test_user_1",
            "password": "<PASSWORD>",
            "confirm_password": "<PASSWORD>",
        }, {"email": "Email address is required!"})
        user = User.get(name="test_user_1")
        self.assertIsNone(user)

    def test_user_signup_missing_password(self):
        self._test_user_signup_missing_fields_helper({
            "username": "test_user_1",
            "email": "test@example.com",
            "confirm_password": "<PASSWORD>",
        }, {
            "password": "Password is required!",
            "confirm_password": "Confirm Password should match password!"
        })
        user = User.get(name="test_user_1")
        self.assertIsNone(user)

    def test_user_signup_missing_confirm_password(self):
        self._test_user_signup_missing_fields_helper({
            "username": "test_user_1",
            "email": "test@example.com",
            "password": "<PASSWORD>",
        }, {"confirm_password": "Confirm Password is required!"})
        user = User.get(name="test_user_1")
        self.assertIsNone(user)

    def test_user_signup_missing_password_mismatch(self):
        self._test_user_signup_missing_fields_helper({
            "username": "test_user_1",
            "email": "test@example.com",
            "password": "<PASSWORD>",
            "confirm_password": "<PASSWORD-1>",
        }, {"confirm_password": "Confirm Password should match password!"})
        user = User.get(name="test_user_1")
        self.assertIsNone(user)

    def test_user_signup_username_exists(self):
        self.create_user()

        self._test_user_signup_helper({
            "username": "test_user_1",
            "email": "test2@gmail.com",
            "password": "<PASSWORD>",
            "confirm_password": "<PASSWORD>",
        }, 200)
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["initial_errors"], {"username": "Another user with username 'test_user_1' exists."})

    def test_user_signup_logged_in(self):
        data = {
            "username": "test_user_1",
            "email": "test@example.com",
            "password": "<PASSWORD>",
            "confirm_password": "<PASSWORD>",
        }
        self._test_user_signup_helper(data, 302)

        response = self.client.get("/signup")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")

        response = self.client.post("/signup", data={
            **data,
            "csrf_token": g.csrf_token,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")

    def _test_user_login_helper(self, data, expected_status_code, include_csrf_token=True):
        self.client.get("/login")
        if include_csrf_token:
            data["csrf_token"] = g.csrf_token
        response = self.client.post("/login", data=data)
        self.assertEqual(response.status_code, expected_status_code)

    def _test_user_login_error(self, data, errors, include_csrf_token=True):
        self._test_user_login_helper(data, 200, include_csrf_token)
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["initial_errors"], errors)
        self.assertTrue(current_user.is_anonymous)

    def test_user_login_success(self):
        self.create_user()

        current_dt = datetime.now(timezone.utc)
        self._test_user_login_helper({
            "username": "test_user_1",
            "password": "<PASSWORD>",
        }, 302)
        self.assertEqual(current_user.name, "test_user_1")
        self.assertFalse(current_user.is_anonymous)
        self.assertGreater(current_user.last_login_at, current_dt)

        self.client.get("/logout")
        self.assertTrue(current_user.is_anonymous)

    def test_user_login_missing_username(self):
        self.create_user()

        self._test_user_login_error({
            "password": "<PASSWORD>",
        }, {"username": "Username is required!"})
        self.assertTrue(current_user.is_anonymous)

    def test_user_login_missing_password(self):
        self.create_user()

        self._test_user_login_error({
            "username": "test_user_1",
        }, {"password": "Password is required!"})
        self.assertTrue(current_user.is_anonymous)

    def test_user_login_missing_csrf_token(self):
        self.create_user()

        self._test_user_login_error({
            "username": "test_user_1",
            "password": "<PASSWORD>",
        }, {"csrf_token": "The CSRF token is missing."}, False)
        self.assertTrue(current_user.is_anonymous)

    def test_user_login_wrong_password(self):
        self.create_user()

        self._test_user_login_error({
            "username": "test_user_1",
            "password": "<PASSWORD-1>",
        }, {"password": "Invalid username or password."})
        self.assertTrue(current_user.is_anonymous)

    def test_user_login_mismatched_password(self):
        self.create_user()
        self.create_user({
            "username": "test_user_2",
            "email": "test2@example.org",
            "password": "<PASSWORD-2>",
            "confirm_password": "<PASSWORD-2>",
        })

        self._test_user_login_error({
            "username": "test_user_1",
            "password": "<PASSWORD-2>",
        },  {"password": "Invalid username or password."})
        self.assertTrue(current_user.is_anonymous)

    def test_user_login_logged_in(self):
        data = {
            "username": "test_user_1",
            "email": "test@example.com",
            "password": "<PASSWORD>",
            "confirm_password": "<PASSWORD>",
        }
        self._test_user_signup_helper(data, 302)

        response = self.client.get("/login")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")

        response = self.client.post("/login", data={
            **data,
            "csrf_token": g.csrf_token,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")

    def test_user_verify_email_success(self):
        self.create_user()
        timestamp = datetime.now(timezone.utc)

        verification_link = self.get_context_variable("verification_link")
        response = self.client.get(verification_link)
        self.assertEqual(response.status_code, 302)
        user = User.get(name="test_user_1")
        self.assertIsNone(user.unconfirmed_email)
        self.assertEqual(user.email, "test@example.com")
        self.assertGreater(user.email_confirmed_at, timestamp)

    def test_user_email_verify_invalid_checksum(self):
        self.create_user()

        user = User.get(name="test_user_1")
        timestamp = int(datetime.now().timestamp())
        checksum = create_email_link_checksum(VERIFY_EMAIL, user.id, "abc@abc.com", timestamp)
        url = url_for(
            "users.verify_email",
            user_id=user.id,
            timestamp=timestamp,
            checksum=checksum,
            _external=True
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertMessageFlashed("Unable to verify email.", "error")

    def test_user_email_verify_missing_checksum(self):
        self.create_user()

        user = User.get(name="test_user_1")
        timestamp = int(datetime.now().timestamp())
        url = url_for(
            "users.verify_email",
            user_id=user.id,
            timestamp=timestamp,
            _external=True
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertMessageFlashed("Unable to verify email.", "error")

    def test_user_email_verify_user_invalid(self):
        self.create_user()

        verification_link = self.get_context_variable("verification_link")
        query = parse_qs(urlparse(verification_link).query)
        url = url_for(
            "users.verify_email",
            user_id=1000,
            timestamp=query.get("timestamp")[0],
            checksum=query.get("checksum")[0],
            _external=True
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertMessageFlashed("User not found.", "error")

    def test_user_email_verify_expired(self):
        self.create_user()
        verification_link = self.get_context_variable("verification_link")

        with freeze_time(datetime.now(timezone.utc) + timedelta(days=1)):
            response = self.client.get(verification_link)
            self.assertEqual(response.status_code, 302)
            self.assertMessageFlashed("Email verification link expired.", "error")

    def test_user_exists_verified_email(self):
        self.create_user()

        verification_link = self.get_context_variable("verification_link")
        response = self.client.get(verification_link)
        self.assertEqual(response.status_code, 302)
        user = User.get(name="test_user_1")
        self.assertEqual(user.email, "test@example.com")

        self._test_user_signup_helper({
            "username": "test_user_2",
            "email": "test@example.com",
            "password": "<PASSWORD>",
            "confirm_password": "<PASSWORD>",
        }, 200)
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["initial_errors"], {"email": "Another user with email 'test@example.com' exists."})

    def test_multiple_users_verify_same_email_fails(self):
        """ Ideally, it shouldn't be possible to create two users with the same unconfirmed email but assuming
            it happens due to some race condition etc. handle the case.
        """
        self.create_user()
        verification_link = self.get_context_variable("verification_link")

        user2 = User.add(name="test_user_2", unconfirmed_email="test@example.com", password="<PASSWORD>")
        db.session.commit()

        timestamp = int(datetime.now().timestamp())
        checksum = create_email_link_checksum(VERIFY_EMAIL, user2.id, "test@example.com", timestamp)
        verification_link2 = url_for(
            "users.verify_email",
            user_id=user2.id,
            timestamp=timestamp,
            checksum=checksum,
            _external=True
        )

        response = self.client.get(verification_link)
        self.assertEqual(response.status_code, 302)
        user = User.get(name="test_user_1")
        self.assertEqual(user.email, "test@example.com")

        response = self.client.get(verification_link2)
        self.assertEqual(response.status_code, 302)
        user2 = User.get(name="test_user_2")
        self.assertIsNone(user2.email)

    def test_resend_verification_email(self):
        self.create_user()

        verification_link = self.get_context_variable("verification_link")
        with freeze_time(datetime.now(timezone.utc) + timedelta(days=1)) as frozen_time:
            # freezing and moving time expires the csrf_token which is constant for a given test request context
            # unless manually deleted
            del g.csrf_token

            response = self.client.get(verification_link)
            self.assertEqual(response.status_code, 302)
            self.assertMessageFlashed("Email verification link expired.", "error")

            self._test_user_login_helper({
                "username": "test_user_1",
                "password": "<PASSWORD>"
            }, 302)

            response = self.client.post("/resend-verification-email", data={"csrf_token": g.csrf_token})
            self.assertEqual(response.status_code, 302)
            new_verification_link = self.get_context_variable("verification_link")
            self.assertNotEqual(new_verification_link, verification_link)

            frozen_time.tick(60)
            response = self.client.get(new_verification_link)
            self.assertEqual(response.status_code, 302)
            user = User.get(name="test_user_1")
            self.assertIsNone(user.unconfirmed_email)
            self.assertEqual(user.email, "test@example.com")

    def test_resend_verification_email_error(self):
        self.create_user()
        response = self.client.post("/resend-verification-email")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.startswith("/login"))

    def test_forgot_username_success(self):
        self.create_user()

        self.client.get("/lost-username")
        response = self.client.post("/lost-username", data={
            "email": "test@example.com",
            "csrf_token": g.csrf_token
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.get_context_variable("username"), "test_user_1")
        self.assertMessageFlashed("Username recovery email sent!", "success")

    def test_forgot_username_logged_in(self):
        self.create_user()
        self.client.post("/login", data={
            "username": "test_user_1",
            "password": "<PASSWORD>",
            "csrf_token": g.csrf_token
        })
        response = self.client.get("/lost-username")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")

        response = self.client.post("/lost-username")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")

    def test_forgot_username_email_not_exist(self):
        self.create_user()
        self.client.get("/lost-username")
        response = self.client.post("/lost-username", data={
            "email": "test1@example.com",
            "csrf_token": g.csrf_token
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(self.get_context_variable("props"))["initial_errors"],
            {"email": "The given email address (test1@example.com) does not exist in our database."}
        )

    def test_forgot_username_email_missing(self):
        self.create_user()
        self.client.get("/lost-username")
        response = self.client.post("/lost-username", data={
            "csrf_token": g.csrf_token
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(self.get_context_variable("props"))["initial_errors"],
            {"email": "Email address is required!"}
        )

    def test_forgot_username_csrf_token_missing(self):
        self.create_user()
        self.client.get("/lost-username")
        response = self.client.post("/lost-username", data={
            "email": "test@example.com"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(self.get_context_variable("props"))["initial_errors"],
            {"csrf_token": "The CSRF token is missing."}
        )

    def _test_forgot_password_helper(self, data, expected_status_code, include_csrf_token=True):
        self.create_user()
        self.client.get("/lost-password")
        if include_csrf_token:
            data["csrf_token"] = g.csrf_token
        response = self.client.post("/lost-password", data=data)
        self.assertEqual(response.status_code, expected_status_code)

    def _test_forgot_password_helper_error(self, data, errors, include_csrf_token=True):
        self._test_forgot_password_helper(data, 200, include_csrf_token)
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["initial_errors"], errors)

    def test_forgot_password_verified_email_success(self):
        self.create_user()
        verification_link = self.get_context_variable("verification_link")
        response = self.client.get(verification_link)
        self.assertEqual(response.status_code, 302)

        self.client.get("/lost-password")
        response = self.client.post("/lost-password", data={
            "username": "test_user_1",
            "email": "test@example.com",
            "csrf_token": g.csrf_token
        })
        self.assertEqual(response.status_code, 302)
        self.assertMessageFlashed("Password reset link sent!", "success")

    def test_forgot_password_logged_in(self):
        self.create_user()
        self.client.post("/login", data={
            "username": "test_user_1",
            "password": "<PASSWORD>",
            "csrf_token": g.csrf_token
        })
        response = self.client.get("/lost-password")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")

        response = self.client.post("/lost-password")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")

    def test_forgot_password_missing_username(self):
        self._test_forgot_password_helper_error({
            "email": "test@example.com",
        }, {"username": "Username is required!"})

    def test_forgot_password_missing_email(self):
        self._test_forgot_password_helper_error({
            "username": "test_user_1",
        }, {"email": "Email address is required!"})

    def test_forgot_password_missing_csrf_token(self):
        self._test_forgot_password_helper_error({
            "username": "test_user_1",
            "email": "test@example.com",
        }, {"csrf_token": "The CSRF token is missing."}, False)

    def test_forgot_password_user_email_mismatch(self):
        self.create_user({
            "username": "test_user_2",
            "email": "test2@example.com",
            "password": "<PASSWORD>",
            "confirm_password": "<PASSWORD>",
        })
        self._test_forgot_password_helper_error({
            "email": "test2@example.com",
            "username": "test_user_1"
        }, {"email": "User with given username (test_user_1) and email (test2@example.com) combination not found."})

    def test_reset_password_logged_in(self):
        self.create_user()
        self.client.post("/login", data={
            "username": "test_user_1",
            "password": "<PASSWORD>",
            "csrf_token": g.csrf_token
        })
        response = self.client.get("/reset-password")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")

        response = self.client.post("/reset-password")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")

    def test_reset_password_success(self):
        self._test_forgot_password_helper({
            "username": "test_user_1",
            "email": "test@example.com",
        }, 302)
        self.assertMessageFlashed("Password reset link sent!", "success")
        reset_password_link = self.get_context_variable("reset_password_link")
        response = self.client.post(reset_password_link, data={
            "password": "<NEW-PASSWORD>",
            "confirm_password": "<NEW-PASSWORD>",
            "csrf_token": g.csrf_token
        })
        self.assertEqual(response.status_code, 302)
        self.assertMessageFlashed("Password reset!", "success")

        # test old password doesn't work
        response = self.client.post("/login", data={
            "username": "test_user_1",
            "password": "<PASSWORD>",
            "csrf_token": g.csrf_token
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(current_user.is_anonymous)
        self.assertEqual(
            json.loads(self.get_context_variable("props"))["initial_errors"],
            {"password": "Invalid username or password."}
        )

        # test new password works
        response = self.client.post("/login", data={
            "username": "test_user_1",
            "password": "<NEW-PASSWORD>",
            "csrf_token": g.csrf_token
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(current_user.is_anonymous)
        self.assertEqual(current_user.name, "test_user_1")

    def test_reset_password_missing_checksum(self):
        self.create_user()
        timestamp = int(datetime.now().timestamp())
        user = User.get(name="test_user_1")
        reset_password_link = url_for("users.reset_password", user_id=user.id, timestamp=timestamp, _external=True)

        response = self.client.get(reset_password_link)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")
        self.assertMessageFlashed("Unable to reset password.", "error")

        response = self.client.post(reset_password_link, data={
            "password": "<NEW-PASSWORD>",
            "confirm_password": "<NEW-PASSWORD>",
            "csrf_token": g.csrf_token
        })
        self.assertEqual(response.location, "/")
        self.assertMessageFlashed("Unable to reset password.", "error")

    def test_reset_password_invalid_user(self):
        self.create_user()
        timestamp = int(datetime.now().timestamp())
        checksum = checksum = create_email_link_checksum(RESET_PASSWORD, 1000, "test@example.com", timestamp)
        reset_password_link = url_for("users.reset_password", user_id=1000, timestamp=timestamp, checksum=checksum, _external=True)

        response = self.client.get(reset_password_link)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")
        self.assertMessageFlashed("User not found.", "error")

        response = self.client.post(reset_password_link, data={
            "password": "<NEW-PASSWORD>",
            "confirm_password": "<NEW-PASSWORD>",
            "csrf_token": g.csrf_token
        })
        self.assertEqual(response.location, "/")
        self.assertMessageFlashed("User not found.", "error")

    def test_reset_password_expired(self):
        self._test_forgot_password_helper({
            "username": "test_user_1",
            "email": "test@example.com",
        }, 302)
        self.assertMessageFlashed("Password reset link sent!", "success")
        reset_password_link = self.get_context_variable("reset_password_link")

        with freeze_time(datetime.now(timezone.utc) + timedelta(days=1)) as frozen_time:
            # freezing and moving time expires the csrf_token which is constant for a given test request context
            # unless manually reset
            g.csrf_token = generate_csrf()

            response = self.client.post(reset_password_link, data={
                "password": "<NEW-PASSWORD>",
                "confirm_password": "<NEW-PASSWORD>",
                "csrf_token": g.csrf_token
            })
            self.assertEqual(response.status_code, 302)
            self.assertMessageFlashed("Password reset link expired.", "error")

    def test_user_signup_without_mtcaptcha_not_configured(self):
        self.app.config["MTCAPTCHA_PRIVATE_KEY"] = ""
        self.app.config["MTCAPTCHA_PUBLIC_KEY"] = ""

        self._test_user_signup_helper({
            "username": "test_user_no_captcha",
            "email": "test_no_captcha@example.com",
            "password": "<PASSWORD>",
            "confirm_password": "<PASSWORD>",
        }, 302)
        self.assertMessageFlashed("Account created. Please check your inbox to complete verification.", "success")

        user = User.get(name="test_user_no_captcha")
        self.assertIsNotNone(user)
        self.assertEqual(user.name, "test_user_no_captcha")
        self.assertEqual(user.unconfirmed_email, "test_no_captcha@example.com")
