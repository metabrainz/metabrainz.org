from unittest.mock import patch

from brainzutils import cache
from flask import url_for
from flask_login import logout_user
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from metabrainz.model import db
from metabrainz.model.moderation_log import ModerationLog
from metabrainz.model.old_username import OldUsername
from metabrainz.model.supporter import Supporter
from metabrainz.model.user import User
from metabrainz.testing import FlaskTestCase


class AdminViewsTestCase(FlaskTestCase):
    def _login_admin(self):
        self.app.config['ADMINS'] = ['admin_user']
        self.temporary_login(self.admin_user)

    def test_index_unauthenticated(self):
        logout_user()
        self.assertStatus(self.client.get(url_for('main_admin.index')), 302)

    def setUp(self):
        super().setUp()
        self.app.config["ADMINS"] = ["admin_user"]

        self.admin_user = User.add(
            name="admin_user",
            unconfirmed_email="admin@metabrainz.org",
            password="adminpassword123"
        )
        db.session.commit()
        self.temporary_login(self.admin_user)

    def test_index_as_admin(self):
        self._login_admin()
        self.assert200(self.client.get(url_for('main_admin.index')))

    def test_supportersview_index_unauthenticated(self):
        logout_user()
        self.assertStatus(self.client.get(url_for('supportersview.index')), 302)

    def tearDown(self):
        db.session.rollback()
        db.session.execute(delete(ModerationLog))
        db.session.execute(delete(Supporter))
        db.session.execute(delete(User))
        db.session.execute(delete(OldUsername))
        db.session.commit()
        cache._r.flushall()
        super().tearDown()

    def test_supportersview_index_as_admin(self):
        self._login_admin()
        self.assert200(self.client.get(url_for('supportersview.index')))

    def test_tokensview_index_unauthenticated(self):
        logout_user()
        self.assertStatus(self.client.get(url_for('tokensview.index')), 302)
    def _test_page_access(self, status_code):
        self.assertStatus(self.client.get(url_for("supporter_admin.index")), status_code)
        self.assertStatus(self.client.get(url_for("user_admin.index")), status_code)
        self.assertStatus(self.client.get(url_for("supportersview.index")), status_code)
        self.assertStatus(self.client.get(url_for("tokensview.index")), status_code)
        self.assertStatus(self.client.get(url_for("statsview.overview")), status_code)
        self.assertStatus(self.client.get(url_for("statsview.top_ips")), status_code)
        self.assertStatus(self.client.get(url_for("statsview.supporters")), status_code)

    def test_tokensview_index_as_admin(self):
        self._login_admin()
        self.assert200(self.client.get(url_for('tokensview.index')))

    def test_statsview_index_unauthenticated(self):
        logout_user()
        self.assertStatus(self.client.get(url_for('statsview.overview')), 302)
    def test_admin_access(self):
        self._test_page_access(200)

    def test_statsview_index_as_admin(self):
        self._login_admin()
        self.assert200(self.client.get(url_for('statsview.overview')))

    def test_statsview_top_ips_unauthenticated(self):
        logout_user()
        self.assertStatus(self.client.get(url_for('statsview.top_ips')), 302)
        self._test_page_access(302)

    def test_statsview_top_ips_as_admin(self):
        self._login_admin()
        self.assert200(self.client.get(url_for('statsview.top_ips')))

    def test_statsview_supporters_unauthenticated(self):
        logout_user()
        self.assertStatus(self.client.get(url_for('statsview.supporters')), 302)
        non_admin_user = self.create_user()
        self.temporary_login(non_admin_user)
        self._test_page_access(302)

    def test_statsview_supporters_as_admin(self):
        self._login_admin()
        self.assert200(self.client.get(url_for('statsview.supporters')))

    def test_commercialsupportersview_index_unauthenticated(self):
        logout_user()
        self.assertStatus(self.client.get(url_for('commercialsupportersview.index')), 302)

    def test_commercialsupportersview_index_as_admin(self):
        self._login_admin()
        self.assert200(self.client.get(url_for('commercialsupportersview.index')))

    def create_user(self):
        user = User.add(
            name="regular_user",
            unconfirmed_email="regular@example.com",
            password="password123"
        )
        db.session.commit()
        return user

    def create_supporter(self):
        user = self.create_user()
        supporter = Supporter.add(
            is_commercial=False,
            contact_name="Test Supporter",
            data_usage_desc="Test usage",
            org_desc="Test org",
            user=user
        )
        db.session.commit()
        return supporter

    def _edit_username(self, user, new_username):
        response = self.client.get(url_for("users-admin.details_view", id=user.id))
        self.assertEqual(response.status_code, 200)
        form = self.get_context_variable("edit_username_form")
        return self.client.post(
            url_for("users-admin.edit_username", user_id=user.id),
            data={
                "username": new_username,
                "csrf_token": form.csrf_token.current_token,
            },
            follow_redirects=False,
        )

    def _edit_supporter_username(self, supporter, new_username):
        supporter.user.email = supporter.user.unconfirmed_email
        supporter.user.unconfirmed_email = None
        db.session.commit()

        response = self.client.get(url_for("supportersview.edit", supporter_id=supporter.id))
        self.assertEqual(response.status_code, 200)
        form = self.get_context_variable("form")
        return self.client.post(
            url_for("supportersview.edit", supporter_id=supporter.id),
            data={
                "username": new_username,
                "email": supporter.user.email,
                "contact_name": supporter.contact_name,
                "state": supporter.state,
                "tier": "None",
                "amount_pledged": "0",
                "csrf_token": form.csrf_token.current_token,
            },
            follow_redirects=False,
        )

    def test_admin_edit_username_rejects_different_case_of_existing_username(self):
        user = self.create_user()

        response = self._edit_username(user, "ADMIN_USER")

        self.assertEqual(response.status_code, 302)
        db.session.refresh(user)
        self.assertEqual(user.name, "regular_user")
        self.assertMessageFlashed("Username is already in use.", "error")

    def test_admin_edit_username_rejects_different_case_of_old_username(self):
        user = self.create_user()
        db.session.add(OldUsername(username="FormerUser"))
        db.session.commit()

        response = self._edit_username(user, "formeruser")

        self.assertEqual(response.status_code, 302)
        db.session.refresh(user)
        self.assertEqual(user.name, "regular_user")
        self.assertMessageFlashed("Username cannot be used.", "error")

    def test_admin_edit_username_treats_case_only_change_as_same_username(self):
        user = self.create_user()

        response = self._edit_username(user, "REGULAR_USER")

        self.assertEqual(response.status_code, 302)
        db.session.refresh(user)
        self.assertEqual(user.name, "regular_user")
        self.assertMessageFlashed("Username is already set to this value.", "error")

    def test_admin_edit_username_treats_exact_change_as_same_username(self):
        user = self.create_user()

        response = self._edit_username(user, "regular_user")

        self.assertEqual(response.status_code, 302)
        db.session.refresh(user)
        self.assertEqual(user.name, "regular_user")
        self.assertMessageFlashed("Username is already set to this value.", "error")
        self.assertIsNone(OldUsername.get("regular_user"))

    def test_admin_supporter_edit_rejects_different_case_of_existing_username(self):
        supporter = self.create_supporter()

        response = self._edit_supporter_username(supporter, "ADMIN_USER")

        self.assertEqual(response.status_code, 200)
        form = self.get_context_variable("form")
        self.assertIn("Username is already in use.", form.username.errors)
        db.session.refresh(supporter.user)
        self.assertEqual(supporter.user.name, "regular_user")

    def test_admin_supporter_edit_rejects_different_case_of_old_username(self):
        supporter = self.create_supporter()
        db.session.add(OldUsername(username="FormerUser"))
        db.session.commit()

        response = self._edit_supporter_username(supporter, "formeruser")

        self.assertEqual(response.status_code, 200)
        form = self.get_context_variable("form")
        self.assertIn("Username cannot be used.", form.username.errors)
        db.session.refresh(supporter.user)
        self.assertEqual(supporter.user.name, "regular_user")

    def test_admin_supporter_edit_reserves_previous_username(self):
        supporter = self.create_supporter()

        response = self._edit_supporter_username(supporter, "RenamedUser")

        self.assertEqual(response.status_code, 302)
        db.session.refresh(supporter.user)
        self.assertEqual(supporter.user.name, "RenamedUser")
        self.assertIsNotNone(OldUsername.get("REGULAR_USER"))

    def test_admin_supporter_edit_handles_concurrent_username_conflict(self):
        supporter = self.create_supporter()

        with patch.object(Supporter, "update", side_effect=IntegrityError(None, None, None)):
            response = self._edit_supporter_username(supporter, "AvailableUser")

        self.assertEqual(response.status_code, 200)
        form = self.get_context_variable("form")
        self.assertIn("Username is already in use.", form.username.errors)
        db.session.refresh(supporter.user)
        self.assertEqual(supporter.user.name, "regular_user")
        self.assertIsNone(OldUsername.get("regular_user"))

    def test_admin_delete_user(self):
        """Test that admin can delete a regular (non-supporter) user."""
        regular_user = self.create_user()
        user_id = regular_user.id

        response = self.client.get(url_for("users-admin.details_view", id=user_id))
        self.assertEqual(response.status_code, 200)

        delete_form = self.get_context_variable("delete_user_form")

        response = self.client.post(
            url_for("users-admin.delete_user", user_id=user_id),
            data={
                "reason": "Test deletion of regular user",
                "confirm": "y",
                "csrf_token": delete_form.csrf_token.current_token,
            },
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 302)

        db.session.expire_all()
        user = User.get(id=user_id)
        self.assertTrue(user.deleted)
        self.assertEqual(user.name, f"deleted-{user_id}")
        self.assertMessageFlashed("User has been deleted.", "success")

    def test_admin_delete_supporter(self):
        """Test that admin cannot delete a user who is a supporter through user portal and
         then test that supporter can be deleted from the supporter portal."""
        supporter = self.create_supporter()
        user_id = supporter.user.id
        supporter_id = supporter.id

        original_username = supporter.user.name

        response = self.client.get(url_for("users-admin.details_view", id=user_id))
        self.assertEqual(response.status_code, 200)

        delete_form = self.get_context_variable("delete_user_form")

        response = self.client.post(
            url_for("users-admin.delete_user", user_id=user_id),
            data={
                "reason": "Test deletion attempt",
                "confirm": "y",
                "csrf_token": delete_form.csrf_token.current_token,
            },
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 302)

        db.session.expire_all()
        user = User.get(id=user_id)
        self.assertFalse(user.deleted)
        self.assertEqual(user.name, "regular_user")

        self.assertTrue(len(self.flashed_messages) > 0)
        message, category = self.flashed_messages[-1]
        self.assertEqual(category, "error")
        self.assertIn("supporter", message.lower())
        self.assertIn(str(supporter_id), message)

        response = self.client.get(url_for("supportersview.delete", supporter_id=supporter_id))
        self.assertEqual(response.status_code, 200)

        form = self.get_context_variable("form")

        response = self.client.post(
            url_for("supportersview.delete", supporter_id=supporter_id),
            data={
                "reason": "Test deletion via supporter portal",
                "confirm": "y",
                "csrf_token": form.csrf_token.current_token,
            },
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("supportersview", response.location)

        db.session.expire_all()
        supporter = Supporter.get(id=supporter_id)
        self.assertIsNone(supporter)

        user = User.get(id=user_id)
        self.assertTrue(user.deleted)
        self.assertEqual(user.name, f"deleted-{user_id}")

        old_username = OldUsername.query.filter_by(username=original_username).first()
        self.assertIsNotNone(old_username)

        self.assertMessageFlashed("Supporter has been deleted.", "success")

    def test_admin_supporter_delete_missing_confirmation(self):
        """Test that deletion fails without confirmation checkbox."""
        supporter = self.create_supporter()

        response = self.client.get(url_for("supportersview.delete", supporter_id=supporter.id))
        form = self.get_context_variable("form")

        response = self.client.post(
            url_for("supportersview.delete", supporter_id=supporter.id),
            data={
                "reason": "Test deletion",
                "csrf_token": form.csrf_token.current_token,
            },
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 200)
        db.session.expire_all()
        supporter = Supporter.get(id=supporter.id)
        self.assertIsNotNone(supporter)

    def test_admin_supporter_delete_missing_reason(self):
        """Test that deletion fails without a reason."""
        supporter = self.create_supporter()

        response = self.client.get(url_for("supportersview.delete", supporter_id=supporter.id))
        form = self.get_context_variable("form")

        response = self.client.post(
            url_for("supportersview.delete", supporter_id=supporter.id),
            data={
                "confirm": "y",
                "csrf_token": form.csrf_token.current_token,
            },
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 200)

        db.session.expire_all()
        supporter = Supporter.get(id=supporter.id)
        self.assertIsNotNone(supporter)

    def test_admin_supporter_delete_requires_auth(self):
        """Test that supporter deletion requires admin authentication."""
        self.client.get("/logout")

        supporter = self.create_supporter()

        response = self.client.get(url_for("supportersview.delete", supporter_id=supporter.id))
        self.assertEqual(response.status_code, 302)
        response = self.client.post(
            url_for("supportersview.delete", supporter_id=supporter.id),
            data={
                "reason": "Unauthorized attempt",
                "confirm": "y",
            }
        )
        self.assertEqual(response.status_code, 302)

        db.session.expire_all()
        supporter = Supporter.get(id=supporter.id)
        self.assertIsNotNone(supporter)

        non_admin_user = User.add(
            name="non_admin_user",
            unconfirmed_email="nonadmin@example.com",
            password="password123"
        )
        db.session.commit()
        self.temporary_login(non_admin_user)

        response = self.client.get(url_for("supportersview.delete", supporter_id=supporter.id))
        self.assertEqual(response.status_code, 302)

        db.session.expire_all()
        supporter = Supporter.get(id=supporter.id)
        self.assertIsNotNone(supporter)

    def _test_verify_email_helper(self, user_id):
        response = self.client.get(url_for("users-admin.details_view", id=user_id))
        self.assertEqual(response.status_code, 200)

        verify_email_form = self.get_context_variable("verify_email_form")

        response = self.client.post(
            url_for("users-admin.verify_user_email", user_id=user_id),
            data={"csrf_token": verify_email_form.csrf_token.current_token},
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 302)

    def test_admin_verify_email(self):
        """ Test manual verification of user emails by admin. """
        user = self.create_user()
        user_id = user.id

        self.assertIsNone(user.email)
        self.assertEqual(user.unconfirmed_email, "regular@example.com")

        self._test_verify_email_helper(user_id)

        user = User.get(id=user_id)
        self.assertEqual(user.email, "regular@example.com")
        self.assertIsNone(user.unconfirmed_email)
        self.assertIsNotNone(user.email_confirmed_at)
        self.assertMessageFlashed(f"Email for {user.name} has been manually verified.", "success")

        # test verifying a new email works
        first_confirmed_at = user.email_confirmed_at
        user.unconfirmed_email = "new@example.com"
        db.session.commit()

        self._test_verify_email_helper(user_id)

        user = User.get(id=user_id)
        self.assertEqual(user.email, "new@example.com")
        self.assertIsNone(user.unconfirmed_email)
        self.assertGreater(user.email_confirmed_at, first_confirmed_at)
        self.assertMessageFlashed(f"Email for {user.name} has been manually verified.", "success")

        # test error if email is already verified
        self._test_verify_email_helper(user_id)

        user = User.get(id=user_id)
        self.assertEqual(user.email, "new@example.com")
        self.assertIsNone(user.unconfirmed_email)
        self.assertMessageFlashed("User's email is already verified", "error")
