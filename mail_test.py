from unittest import mock
import requests
import requests_mock

from flask import current_app
from metabrainz.testing import FlaskTestCase
from metabrainz.mail import NotificationSender


class NotificationSenderTest(FlaskTestCase):
    def setUp(self):
        super(NotificationSenderTest, self).setUp()
        self.notifications = [
            {
                "musicbrainz_row_id": 3,
                "project": "metabrainz",
                "recipient": "user@example.com",
                "sent_from": "noreply@project.org",
                "reply_to": "noreply@project.org",
                "send_email": True,
                "subject": "test",
                "body": "test-123",
                "important": False,
                "expire_age": 30,
                "email_id": "c7d7b431-7130-4a3c-ad8a-17cdd5ebdf2d",
                "id": 6,
            },
            {
                "musicbrainz_row_id": 1,
                "project": "musicbrainz",
                "recipient": "user@example.com",
                "sent_from": "noreply@project.org",
                "reply_to": "noreply@project.org",
                "send_email": True,
                "template_id": "verify-email",
                "template_params": {"reason": "verify"},
                "important": False,
                "expire_age": 30,
                "email_id": "c512e637-21ff-45b1-a58a-03412224b48b",
                "id": 4,
            },
        ]
        self.service = NotificationSender(self.notifications)

    @requests_mock.Mocker()
    def test_send_html_mail(self, mock_request):
        single_mail_endpoint = current_app.config["MB_MAIL_SERVER_URI"] + "/send_single"
        mock_request.post(single_mail_endpoint, 200)
        expected_payload = {
            "from": self.notifications[1]["sent_from"],
            "to": self.notifications[1]["recipient"],
            "template_id": self.notifications[1]["template_id"],
            "params": self.notifications[1]["template_params"],
            "language": None,
            "in_reply_to": [],
            "sender": None,
            "references": [],
            "reply_to": None,
            "message_id": self.notifications[1]["email_id"],
        }

        self.service.send_html_mail(
            from_addr=self.notifications[1]["sent_from"],
            recipient=self.notifications[1]["recipient"],
            template_id=self.notifications[1]["template_id"],
            template_params=self.notifications[1]["template_params"],
        )

        self.assertEqual(mock_request.last_request.json(), expected_payload)

        mock_request.post(single_mail_endpoint, 500)

        with self.assertRaises(requests.exceptions.HTTPError) as err:
            self.service.send_html_mail(
                from_addr=self.notifications[1]["sent_from"],
                recipient=self.notifications[1]["recipient"],
                template_id=self.notifications[1]["template_id"],
                template_params=self.notifications[1]["template_params"],
            )

        self.assertEqual(err.exception.response.status_code, 500)
