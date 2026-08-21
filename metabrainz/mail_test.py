import smtplib
import unittest
from unittest.mock import patch

from flask import Flask

from metabrainz.mail import MailException, send_mail


class SendMailTestCase(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=False,
            SMTP_SERVER="smtp.example.com",
            SMTP_PORT=25,
            MAIL_FROM_DOMAIN="metabrainz.org",
        )

    @patch("metabrainz.mail.smtplib.SMTP")
    def test_uses_bare_recipient_for_header_and_envelope(self, smtp):
        with self.app.app_context():
            send_mail(
                subject="Test subject",
                text="Test body",
                recipients=["recipient@example.com"],
            )
        from_addr, recipients, message = smtp.return_value.sendmail.call_args.args
        self.assertEqual(from_addr, "noreply@metabrainz.org")
        self.assertEqual(recipients, ["recipient@example.com"])
        self.assertIn("To: recipient@example.com", message)

    @patch("metabrainz.mail.smtplib.SMTP")
    def test_wraps_smtp_delivery_errors(self, smtp):
        smtp.return_value.sendmail.side_effect = smtplib.SMTPDataError(550, b"header syntax")

        with self.app.app_context(), self.assertRaises(MailException):
            send_mail(
                subject="Test subject",
                text="Test body",
                recipients=["recipient@example.com"],
            )
