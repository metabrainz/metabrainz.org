import re
from unittest.mock import patch

from brainzutils import cache
from flask import url_for
from flask_login import logout_user
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from metabrainz.model import db
from metabrainz.model.moderation_log import ModerationLog
from metabrainz.model.oauth.client import OAuth2Client, OAuth2ClientPrivilege
from metabrainz.model.old_username import OldUsername
from metabrainz.model.supporter import Supporter
from metabrainz.model.token import Token
from metabrainz.model.token_log import TokenLog
from metabrainz.model.user import User
from metabrainz.model.webhook import EVENT_USER_UPDATED
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
        # token_log references token, so it has to go first
        db.session.execute(delete(TokenLog))
        db.session.execute(delete(Token))
        db.session.execute(delete(Supporter))
        db.session.execute(delete(User))
        db.session.execute(delete(OldUsername))
        db.session.execute(delete(OAuth2Client))
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

    def test_stats_pages_render_token_log_row_without_supporter(self):
        """ TokenLog.supporter_id is nullable, so the stats pages must not
        dereference the relationship without a guard.

        An admin who has no supporter row of their own generating a token for
        somebody else is exactly how a NULL lands there; the FK is also
        ON DELETE SET NULL, so deleting a supporter produces the same shape. """
        self._login_admin()
        supporter = self.create_supporter()
        Token.generate_token(supporter.id)

        record = TokenLog.query.one()
        self.assertIsNone(record.supporter_id)

        for endpoint in ("statsview.token_log", "statsview.overview"):
            with self.subTest(endpoint=endpoint):
                response = self.client.get(url_for(endpoint))
                self.assert200(response)
                self.assertIn("Deleted Supporter", response.get_data(as_text=True))

    def _create_search_supporter(self, username, email, org_name):
        user = User.add(
            name=username,
            unconfirmed_email=email,
            password="password123",
        )
        supporter = Supporter.add(
            is_commercial=False,
            contact_name=f"{org_name} contact",
            data_usage_desc="Test usage",
            org_name=org_name,
            user=user,
        )
        db.session.commit()
        return supporter

    def test_supporter_search_includes_exact_username_org_and_pending_email(self):
        exact = self._create_search_supporter(
            "exact-supporter",
            "pending@example.com",
            "Exact Organization",
        )
        partial = self._create_search_supporter(
            "exact-supporter-extra",
            "other@example.com",
            "Exact Organization Europe",
        )

        self.client.get(
            url_for("supportersview.index"),
            query_string={"search": "  exact organization  "},
        )
        supporters = self.get_context_variable("supporters")
        self.assertEqual([supporter.id for supporter in supporters], [exact.id, partial.id])

        self.client.get(
            url_for("supportersview.index"),
            query_string={"search": "EXACT-SUPPORTER"},
        )
        supporters = self.get_context_variable("supporters")
        self.assertEqual([supporter.id for supporter in supporters], [exact.id, partial.id])

        self.client.get(
            url_for("supportersview.index"),
            query_string={"search": "pending@example.com"},
        )
        supporters = self.get_context_variable("supporters")
        self.assertEqual([supporter.id for supporter in supporters], [exact.id])

    def test_user_search_includes_pending_email_and_ranks_exact_username_first(self):
        exact = User.add(
            name="exact-user",
            unconfirmed_email="pending-user@example.com",
            password="password123",
        )
        partial = User.add(
            name="exact-user-extra",
            unconfirmed_email="other-user@example.com",
            password="password123",
        )
        db.session.commit()

        self.client.get(
            url_for("users-admin.index_view"),
            query_string={"search": "EXACT-USER"},
        )
        users = self.get_context_variable("data")
        self.assertEqual([user.id for user in users], [exact.id, partial.id])

        self.client.get(
            url_for("users-admin.index_view"),
            query_string={"search": "pending-user@example.com"},
        )
        users = self.get_context_variable("data")
        self.assertEqual([user.id for user in users], [exact.id])

    def test_supporter_edit_shows_unconfirmed_email_with_verification_status(self):
        supporter = self.create_supporter()

        response = self.client.get(url_for("supportersview.edit", supporter_id=supporter.id))

        self.assert200(response)
        body = response.get_data(as_text=True)
        self.assertIn("regular@example.com", body)
        self.assertIn("Unverified", body)

    def test_supporter_edit_shows_confirmed_email_with_verification_status(self):
        supporter = self.create_supporter()
        supporter.user.email = "confirmed@example.com"
        supporter.user.unconfirmed_email = "pending@example.com"
        db.session.commit()

        response = self.client.get(url_for("supportersview.edit", supporter_id=supporter.id))

        self.assert200(response)
        body = response.get_data(as_text=True)
        self.assertIn("confirmed@example.com", body)
        self.assertIn("Verified", body)
        self.assertNotIn("Unverified", body)

    def test_supporter_edit_cannot_change_email(self):
        """ The address is changed from the supporter page, not from this form.

        Posting one anyway must be ignored rather than quietly applied, since
        the form carries no answer to whether it should count as confirmed. """
        supporter = self.create_supporter()
        response = self.client.get(url_for("supportersview.edit", supporter_id=supporter.id))
        self.assert200(response)
        form = self.get_context_variable("form")
        self.assertFalse(hasattr(form, "email"))

        response = self.client.post(
            url_for("supportersview.edit", supporter_id=supporter.id),
            data={
                "username": supporter.user.name,
                "email": "updated@example.com",
                "contact_name": supporter.contact_name,
                "state": supporter.state,
                "tier": "None",
                "amount_pledged": "0",
                "csrf_token": form.csrf_token.current_token,
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        db.session.refresh(supporter.user)
        self.assertIsNone(supporter.user.email)
        self.assertEqual(supporter.user.unconfirmed_email, "regular@example.com")

    def test_old_username_page_can_be_searched(self):
        matching = OldUsername(username="Former Exact User")
        db.session.add_all([
            matching,
            OldUsername(username="Unrelated User"),
        ])
        db.session.commit()

        self.client.get(
            url_for("old-username-admin.index_view"),
            query_string={"search": "former exact"},
        )
        old_usernames = self.get_context_variable("data")
        self.assertEqual([old_username.id for old_username in old_usernames], [matching.id])

    def _edit_username(self, user, new_username, reason=None):
        response = self.client.get(url_for("users-admin.details_view", id=user.id))
        self.assertEqual(response.status_code, 200)
        form = self.get_context_variable("edit_username_form")
        data = {
            "username": new_username,
            "csrf_token": form.csrf_token.current_token,
        }
        if reason is not None:
            data["reason"] = reason
        return self.client.post(
            url_for("users-admin.edit_username", user_id=user.id),
            data=data,
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

    def test_admin_edit_username_logs_optional_reason(self):
        user = self.create_user()

        response = self._edit_username(
            user,
            "RenamedUser",
            reason="  Requested by the account owner.  ",
        )

        self.assertEqual(response.status_code, 302)
        log = ModerationLog.query.filter_by(
            user_id=user.id,
            action="edit_username",
        ).one()
        self.assertEqual(
            log.reason,
            "Username changed from 'regular_user' to 'RenamedUser'. "
            "Requested by the account owner.",
        )

    def test_admin_edit_username_keeps_existing_message_without_reason(self):
        user = self.create_user()

        response = self._edit_username(user, "RenamedUser")

        self.assertEqual(response.status_code, 302)
        log = ModerationLog.query.filter_by(
            user_id=user.id,
            action="edit_username",
        ).one()
        self.assertEqual(
            log.reason,
            "Username changed from 'regular_user' to 'RenamedUser'.",
        )

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

    def _change_email_from_user_page(self, user_id, email, confirmed=False, reason=None):
        self.assert200(self.client.get(url_for("users-admin.details_view", id=user_id)))
        form = self.get_context_variable("change_email_form")
        data = {"email": email, "csrf_token": form.csrf_token.current_token}
        if confirmed:
            data["confirmed"] = "y"
        if reason is not None:
            data["reason"] = reason
        return self.client.post(
            url_for("users-admin.change_email", user_id=user_id),
            data=data,
            follow_redirects=False,
        )

    def _change_email_from_supporter_page(self, supporter_id, email, confirmed=False):
        self.assert200(self.client.get(url_for("supportersview.details", supporter_id=supporter_id)))
        form = self.get_context_variable("change_email_form")
        data = {"email": email, "csrf_token": form.csrf_token.current_token}
        if confirmed:
            data["confirmed"] = "y"
        return self.client.post(
            url_for("supportersview.change_email", supporter_id=supporter_id),
            data=data,
            follow_redirects=False,
        )

    @patch("metabrainz.model.user.Webhook.create_delivery_for_event")
    def test_admin_change_email_confirmed(self, create_delivery):
        user = self.create_user()
        user.email = "old@example.com"
        user.unconfirmed_email = "stale@example.com"
        db.session.commit()
        user_id = user.id

        response = self._change_email_from_user_page(
            user_id, "new@example.com", confirmed=True, reason="Owner asked over the phone."
        )
        self.assertEqual(response.status_code, 302)

        user = User.get(id=user_id)
        self.assertEqual(user.email, "new@example.com")
        # the superseded pending address must go, or its verification link could
        # later overwrite the address that was just confirmed
        self.assertIsNone(user.unconfirmed_email)
        self.assertIsNotNone(user.email_confirmed_at)

        event, payload = create_delivery.call_args.args
        self.assertEqual(event, EVENT_USER_UPDATED)
        self.assertEqual(payload["old"], {"email": "old@example.com"})
        self.assertEqual(payload["new"], {"email": "new@example.com"})

        log = ModerationLog.query.filter_by(user_id=user_id, action="change_email").one()
        self.assertIn("new@example.com", log.reason)
        self.assertIn("confirmed", log.reason)
        self.assertIn("Owner asked over the phone.", log.reason)

    @patch("metabrainz.model.user.Webhook.create_delivery_for_event")
    def test_admin_change_email_unconfirmed_sends_verification(self, create_delivery):
        user = self.create_user()
        user.email = "old@example.com"
        db.session.commit()
        user_id = user.id

        response = self._change_email_from_user_page(user_id, "new@example.com")
        self.assertEqual(response.status_code, 302)

        user = User.get(id=user_id)
        # the confirmed address keeps working until the user follows the link
        self.assertEqual(user.email, "old@example.com")
        self.assertEqual(user.unconfirmed_email, "new@example.com")

        # nothing downstream has changed yet, so nothing is announced
        create_delivery.assert_not_called()

        # rendering the verification email is what puts this in the context
        self.assertIsNotNone(self.get_context_variable("verification_link"))
        # the admin variant, which says who made the change instead of naming an
        # IP address that would be the admin's rather than the user's
        self.assertTemplateUsed("email/user-email-address-verification-admin.txt")

        log = ModerationLog.query.filter_by(user_id=user_id, action="change_email").one()
        self.assertIn("pending verification", log.reason)

    def test_admin_change_email_warns_when_address_already_in_use(self):
        """ Two accounts may share an address; the admin is told, not stopped. """
        user = self.create_user()
        user_id = user.id

        response = self._change_email_from_user_page(user_id, "admin@metabrainz.org")

        self.assertEqual(response.status_code, 302)
        user = User.get(id=user_id)
        self.assertEqual(user.unconfirmed_email, "admin@metabrainz.org")
        self.assertMessageFlashed("admin@metabrainz.org is also used by admin_user.", "warning")

    def test_admin_email_in_use_lookup_reports_other_accounts(self):
        user = self.create_user()

        response = self.client.post(
            url_for("users-admin.email_in_use", user_id=user.id),
            json={"email": "ADMIN@metabrainz.org"},
        )

        self.assert200(response)
        self.assertEqual(
            response.json["accounts"],
            [{"name": "admin_user", "confirmed": False}],
        )

        # the account being edited is never reported against itself
        response = self.client.post(
            url_for("users-admin.email_in_use", user_id=user.id),
            json={"email": user.unconfirmed_email},
        )
        self.assert200(response)
        self.assertEqual(response.json["accounts"], [])

    @patch("metabrainz.model.user.Webhook.create_delivery_for_event")
    def test_supporter_change_email_matches_user_page(self, create_delivery):
        """ Both pages route through one implementation, so both must agree. """
        supporter = self.create_supporter()
        supporter.user.email = "old@example.com"
        db.session.commit()
        supporter_id, user_id = supporter.id, supporter.user.id

        response = self._change_email_from_supporter_page(
            supporter_id, "new@example.com", confirmed=True
        )
        self.assertEqual(response.status_code, 302)

        user = User.get(id=user_id)
        self.assertEqual(user.email, "new@example.com")
        self.assertIsNone(user.unconfirmed_email)
        self.assertIsNotNone(user.email_confirmed_at)

        event, payload = create_delivery.call_args.args
        self.assertEqual(event, EVENT_USER_UPDATED)
        self.assertEqual(payload["new"], {"email": "new@example.com"})

        self.assertEqual(
            ModerationLog.query.filter_by(user_id=user_id, action="change_email").count(), 1
        )

    @patch("metabrainz.model.user.Webhook.create_delivery_for_event")
    def test_admin_change_email_refuses_deleted_account(self, create_delivery):
        """ delete() scrubs the address; changing it would write PII back. """
        user = self.create_user()
        user_id = user.id
        user.delete()
        db.session.commit()

        response = self._change_email_from_user_page(user_id, "new@example.com")

        self.assertEqual(response.status_code, 302)
        user = User.get(id=user_id)
        self.assertIsNone(user.email)
        self.assertIsNone(user.unconfirmed_email)
        create_delivery.assert_not_called()
        self.assertMessageFlashed(
            "This account has been deleted, so its email cannot be changed.", "error"
        )

    def test_admin_change_email_warns_that_a_confirmed_duplicate_cannot_verify(self):
        """ users.verify_email rejects an address confirmed elsewhere, so the
        link sent by the unconfirmed path would be a dead end. """
        holder = self.create_user()
        holder.email = "shared@example.com"
        db.session.commit()

        supporter = self._create_search_supporter("other", "other@example.com", "Other Org")
        user_id = supporter.user.id

        response = self._change_email_from_user_page(user_id, "shared@example.com")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.get(id=user_id).unconfirmed_email, "shared@example.com")
        self.assertMessageFlashed("shared@example.com is also used by regular_user.", "warning")
        self.assertMessageFlashed(
            "shared@example.com is already confirmed on another account, so the verification "
            "link will not work. Tick 'Mark this address as confirmed' to set it anyway.",
            "error",
        )

    def test_confirmed_email_exists_matches_case_insensitively(self):
        """ Mailboxes are case insensitive; an exact match let a differently
        cased address past every duplicate guard. """
        user = self.create_user()
        user.email = "bob@example.com"
        db.session.commit()

        self.assertTrue(User.confirmed_email_exists("Bob@Example.com"))
        self.assertFalse(User.confirmed_email_exists("Bob@Example.com", exclude_user_id=user.id))

    def test_admin_change_email_rejects_invalid_address(self):
        user = self.create_user()
        user_id = user.id

        response = self._change_email_from_user_page(user_id, "not-an-email")

        self.assertEqual(response.status_code, 302)
        user = User.get(id=user_id)
        self.assertEqual(user.unconfirmed_email, "regular@example.com")
        self.assertMessageFlashed("This is not a valid email address", "error")

    def test_admin_reject_supporter_with_unconfirmed_email(self):
        """ Rejecting a supporter who has not confirmed their email notifies the unconfirmed address. """
        self._login_admin()
        supporter = self.create_supporter()
        supporter_id = supporter.id
        self.assertIsNone(supporter.user.email)

        with patch("metabrainz.model.supporter.send_mail") as send_mail:
            response = self.client.get(
                url_for("supportersview.reject"),
                query_string={"supporter_id": supporter_id},
            )

        self.assertStatus(response, 302)
        self.assertEqual(send_mail.call_args.kwargs["recipients"], ["regular@example.com"])

        supporter = Supporter.get(id=supporter_id)
        self.assertEqual(supporter.state, "rejected")

    def test_admin_reject_supporter_without_any_email(self):
        """ Rejecting a supporter who has no email address at all does not attempt to send mail. """
        self._login_admin()
        supporter = self.create_supporter()
        supporter_id = supporter.id
        supporter.user.unconfirmed_email = None
        db.session.commit()

        with patch("metabrainz.model.supporter.send_mail") as send_mail:
            response = self.client.get(
                url_for("supportersview.reject"),
                query_string={"supporter_id": supporter_id},
            )

        self.assertStatus(response, 302)
        send_mail.assert_not_called()

        supporter = Supporter.get(id=supporter_id)
        self.assertEqual(supporter.state, "rejected")

    def create_oauth_client(self, **overrides):
        client = OAuth2Client(
            client_id="test-client-id",
            client_secret="test-client-secret",
            owner_id=1,
            name="Test Application",
            description="A test application.",
            website="https://example.org",
            redirect_uris=["https://example.org/callback"],
            privileges=OAuth2ClientPrivilege.REMEMBER_ME.value,
            **overrides,
        )
        db.session.add(client)
        db.session.commit()
        return client

    def _oauth_client_edit_url(self, client):
        return url_for("oauth-clients-admin.edit_view", id=client.id)

    @staticmethod
    def _rendered_control(body, field_name):
        """ The tag name of the form control rendered for a field, or None.

        wtforms emits attributes in alphabetical order, so matching on the name
        attribute keeps this independent of where it lands in the tag. """
        match = re.search(rf'<(input|textarea|select)[^>]*\bname="{re.escape(field_name)}"', body)
        return match.group(1) if match else None

    def test_oauth_client_edit_page_renders_details(self):
        self._login_admin()
        client = self.create_oauth_client()

        response = self.client.get(self._oauth_client_edit_url(client))

        self.assert200(response)
        body = response.get_data(as_text=True)
        # assert on the rendered controls, not bare substrings: the field names also
        # occur in labels and CSS classes, so a column dropped from form_columns
        # would otherwise still look present. name and website must be single line
        # inputs - flask-admin renders Text columns as textareas unless overridden.
        self.assertEqual(self._rendered_control(body, "name"), "input")
        self.assertEqual(self._rendered_control(body, "website"), "input")
        self.assertEqual(self._rendered_control(body, "description"), "textarea")
        self.assertEqual(self._rendered_control(body, "redirect_uris"), "textarea")
        self.assertIn('id="privileges"', body)

    def test_oauth_client_edit_updates_details(self):
        self._login_admin()
        client = self.create_oauth_client()
        client_id = client.id

        self.assert200(self.client.get(self._oauth_client_edit_url(client)))
        form = self.get_context_variable("form")
        response = self.client.post(self._oauth_client_edit_url(client), data={
            "csrf_token": form.csrf_token.current_token,
            "name": "Renamed Application",
            "description": "An updated description.",
            "website": "https://renamed.example.org",
            "redirect_uris": "https://renamed.example.org/cb\nhttp://localhost:8080/cb",
            "privileges": [str(OAuth2ClientPrivilege.CLIENT_CREDENTIALS.value)],
        })

        self.assertStatus(response, 302)
        db.session.expire_all()
        updated = db.session.get(OAuth2Client, client_id)
        self.assertEqual(updated.name, "Renamed Application")
        self.assertEqual(updated.description, "An updated description.")
        self.assertEqual(updated.website, "https://renamed.example.org")
        self.assertEqual(
            updated.redirect_uris,
            ["https://renamed.example.org/cb", "http://localhost:8080/cb"],
        )
        self.assertEqual(updated.privileges, OAuth2ClientPrivilege.CLIENT_CREDENTIALS.value)
        # the client identity must survive an edit untouched
        self.assertEqual(updated.client_id, "test-client-id")
        self.assertEqual(updated.client_secret, "test-client-secret")
        self.assertEqual(updated.owner_id, 1)

    def test_oauth_client_edit_rejects_non_http_redirect_uri(self):
        self._login_admin()
        client = self.create_oauth_client()
        client_id = client.id

        self.assert200(self.client.get(self._oauth_client_edit_url(client)))
        form = self.get_context_variable("form")
        response = self.client.post(self._oauth_client_edit_url(client), data={
            "csrf_token": form.csrf_token.current_token,
            "name": "Test Application",
            "description": "A test application.",
            "website": "https://example.org",
            "redirect_uris": "javascript:alert(1)",
            "privileges": [],
        })

        self.assert200(response)
        db.session.expire_all()
        unchanged = db.session.get(OAuth2Client, client_id)
        self.assertEqual(unchanged.redirect_uris, ["https://example.org/callback"])

    def test_oauth_client_edit_rejects_empty_redirect_uris(self):
        self._login_admin()
        client = self.create_oauth_client()
        client_id = client.id

        for blank in ("   \n  ", ""):
            with self.subTest(redirect_uris=blank):
                self.assert200(self.client.get(self._oauth_client_edit_url(client)))
                form = self.get_context_variable("form")
                response = self.client.post(self._oauth_client_edit_url(client), data={
                    "csrf_token": form.csrf_token.current_token,
                    "name": "Test Application",
                    "description": "A test application.",
                    "website": "https://example.org",
                    "redirect_uris": blank,
                    "privileges": [],
                })

                self.assert200(response)
                # the specific message must survive the InputRequired that
                # flask-admin appends for this NOT NULL column
                self.assertIn(
                    "At least one authorization callback URL is required.",
                    response.get_data(as_text=True),
                )
                db.session.expire_all()
                unchanged = db.session.get(OAuth2Client, client_id)
                self.assertEqual(unchanged.redirect_uris, ["https://example.org/callback"])

    def test_oauth_client_edit_reports_every_invalid_redirect_uri(self):
        self._login_admin()
        client = self.create_oauth_client()

        self.assert200(self.client.get(self._oauth_client_edit_url(client)))
        form = self.get_context_variable("form")
        response = self.client.post(self._oauth_client_edit_url(client), data={
            "csrf_token": form.csrf_token.current_token,
            "name": "Test Application",
            "description": "A test application.",
            "website": "https://example.org",
            "redirect_uris": "ftp://one.example/cb\nhttps://ok.example/cb\nnot a url",
            "privileges": [],
        })

        self.assert200(response)
        # assert on the errors, not the body: the textarea echoes every submitted
        # line back, so matching the URIs there passes even if nothing was reported
        errors = self.get_context_variable("form").redirect_uris.errors
        self.assertEqual(errors, [
            "'ftp://one.example/cb' must use http or https.",
            "'not a url' is not a valid URL.",
        ])
