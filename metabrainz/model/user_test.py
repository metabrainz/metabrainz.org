from sqlalchemy.exc import IntegrityError

from metabrainz.model import db
from metabrainz.model.old_username import OldUsername
from metabrainz.model.user import User, UsernameNotAllowedException
from metabrainz.testing import FlaskTestCase


class UserModelTestCase(FlaskTestCase):

    def test_username_lookup_and_uniqueness_are_case_insensitive(self):
        user = User.add(
            name="MixedCaseUser",
            unconfirmed_email="mixed@example.com",
            password="<PASSWORD>",
        )
        db.session.commit()

        self.assertEqual(User.get(name="mixedcaseuser"), user)
        self.assertEqual(User.get(name="MIXEDCASEUSER"), user)
        self.assertEqual(user.name, "MixedCaseUser")

        User.add(
            name="mixedcaseuser",
            unconfirmed_email="duplicate@example.com",
            password="<PASSWORD>",
        )
        with self.assertRaises(IntegrityError):
            db.session.commit()

    def test_add_trims_username_whitespace(self):
        user = User.add(
            name="  test-user \t",
            unconfirmed_email="trimmed@example.com",
            password="<PASSWORD>",
        )
        db.session.commit()

        self.assertEqual(user.name, "test-user")
        self.assertEqual(User.get(name="test-user"), user)

    def test_name_assignment_trims_username_whitespace(self):
        user = User.add(
            name="test-user",
            unconfirmed_email="trimmed@example.com",
            password="<PASSWORD>",
        )

        user.name = "  renamed-user \t"

        self.assertEqual(user.name, "renamed-user")

    def test_add_checks_trimmed_username_against_old_usernames(self):
        db.session.add(OldUsername(username="reserved-user"))
        db.session.commit()

        with self.assertRaises(UsernameNotAllowedException):
            User.add(
                name="  reserved-user \t",
                unconfirmed_email="reserved@example.com",
                password="<PASSWORD>",
            )

    def test_add_requires_unconfirmed_email(self):
        with self.assertRaisesRegex(ValueError, "Email address is required."):
            User.add(name="missing-email-user", unconfirmed_email=None, password="<PASSWORD>")

        with self.assertRaisesRegex(ValueError, "Email address is required."):
            User.add(name="blank-email-user", unconfirmed_email=" ", password="<PASSWORD>")

    def test_manual_verify_rejects_duplicate_confirmed_email(self):
        moderator = User.add(name="moderator", unconfirmed_email="moderator@example.com", password="<PASSWORD>")
        existing_user = User.add(name="existing-user", unconfirmed_email="same@example.com", password="<PASSWORD>")
        new_user = User.add(name="new-user", unconfirmed_email="same@example.com", password="<PASSWORD>")
        db.session.add_all([moderator, existing_user, new_user])
        db.session.commit()

        existing_user.verify_email_manually(moderator, "Verify existing user.")
        db.session.commit()

        with self.assertRaisesRegex(ValueError, "The email is already associated with an another account."):
            new_user.verify_email_manually(moderator, "Verify duplicate email.")
