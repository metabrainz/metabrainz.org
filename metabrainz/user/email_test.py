import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from metabrainz import create_app
from metabrainz.user.email import send_forgot_username_email, send_verification_email


class UserEmailTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app(config_path=str(Path(__file__).resolve().parents[2] / "config.py"))
        cls.app.config.update(DEBUG=False, TESTING=True)

    def setUp(self):
        self.context = self.app.test_request_context()
        self.context.push()

    def tearDown(self):
        self.context.pop()

    @patch("metabrainz.user.email.send_mail")
    def test_verification_uses_bare_address_for_all_usernames(self, send_mail):
        usernames = [
            "person@example.com",
            "VSR@03",
            "Michal Babička",
            "Surname, Given",
        ]

        for user_id, username in enumerate(usernames, start=1):
            with self.subTest(username=username):
                email = f"recipient{user_id}@example.com"
                user = SimpleNamespace(id=user_id, name=username, unconfirmed_email=email)
                send_verification_email(
                    user,
                    "Please verify your email address",
                    "email/user-email-address-verification.txt",
                )
                self.assertEqual(send_mail.call_args.kwargs["recipients"], [email])

    @patch("metabrainz.user.email.send_mail")
    def test_forgot_username_uses_pending_address(self, send_mail):
        user = SimpleNamespace(
            name="pending-user",
            email=None,
            unconfirmed_email="pending@example.com",
            get_email_any=lambda: "pending@example.com",
        )

        send_forgot_username_email(user)

        self.assertEqual(send_mail.call_args.kwargs["recipients"], ["pending@example.com"])

    @patch("metabrainz.user.email.send_mail")
    def test_forgot_username_rejects_missing_address(self, send_mail):
        user = SimpleNamespace(
            name="no-address-user",
            email=None,
            unconfirmed_email=None,
            get_email_any=lambda: None,
        )

        with self.assertRaisesRegex(ValueError, "without a recipient address"):
            send_forgot_username_email(user)

        send_mail.assert_not_called()
