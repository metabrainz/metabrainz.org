from metabrainz.model import db
from metabrainz.model.user import User
from metabrainz.testing import FlaskTestCase


class UserModelTestCase(FlaskTestCase):

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
