from unittest import mock
import requests
import requests_mock
import orjson

from flask import current_app
from metabrainz.testing import FlaskTestCase
from metabrainz.mail import NotificationSender, FAILED_MAIL_HASH_KEY


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
                "important": True,
                "expire_age": 30,
                "email_id": "c512e637-21ff-45b1-a58a-03412224b48b",
                "id": 4,
            },
        ]
        self.service = NotificationSender(self.notifications)

    @requests_mock.Mocker()
    def test_send_html_mail(self, mock_request):
        single_mail_endpoint = current_app.config["MB_MAIL_SERVER_URI"] + "/send_single"
        mock_request.post(single_mail_endpoint, status_code=200)
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
            message_id=self.notifications[1]["email_id"]
        )

        self.assertEqual(mock_request.last_request.json(), expected_payload)

        # Error on the mb-mail server side.
        mock_request.post(single_mail_endpoint, status_code=500)

        with self.assertRaises(requests.exceptions.HTTPError) as err:
            self.service.send_html_mail(
                from_addr=self.notifications[1]["sent_from"],
                recipient=self.notifications[1]["recipient"],
                template_id=self.notifications[1]["template_id"],
                template_params=self.notifications[1]["template_params"],
                message_id=self.notifications[1]["email_id"]
            )

        self.assertEqual(err.exception.response.status_code, 500)

    @mock.patch("metabrainz.mail.cache")
    @mock.patch("metabrainz.mail.NotificationSender.send_html_mail")
    @mock.patch("metabrainz.mail.send_mail")
    def test_send_notifications(self, mock_send_mail, mock_send_html_mail, mock_cache):
        mock_send_mail.return_value = None
        mock_send_html_mail.return_value = None

        self.service._send_notifications(self.notifications)

        # Plain text mail notification.
        mock_send_mail.assert_called_once_with(
            subject=self.notifications[0]["subject"],
            text=self.notifications[0]["body"],
            recipients=[self.notifications[0]["recipient"]],
            from_addr=self.notifications[0]["sent_from"],
        )
        # HTML mail notification.
        mock_send_html_mail.assert_called_once_with(
            from_addr=self.notifications[1]["sent_from"],
            recipient=self.notifications[1]["recipient"],
            template_id=self.notifications[1]["template_id"],
            template_params=self.notifications[1]["template_params"],
            message_id=self.notifications[1]["email_id"]            
        )

        # MB-mail failure
        mock_send_html_mail.side_effect = Exception()
        mock_cache.return_value = 1

        self.service._send_notifications(self.notifications)

        args, _ = mock_cache.hset.call_args
        self.assertEqual(args[0], FAILED_MAIL_HASH_KEY)
        self.assertIsInstance(args[1], str)
        self.assertEqual(args[2], orjson.dumps(self.notifications[1]))

        

    @mock.patch("metabrainz.mail.NotificationSender._send_notifications")
    @mock.patch("metabrainz.mail.mark_notifications_sent")
    @mock.patch("metabrainz.mail.filter_non_digest_notifications")
    def test_send_immediate_notifications(self, mock_filter, mock_mark_sent, mock_send):
        mock_filter.return_value = []
        mock_mark_sent.return_value = None
        mock_send.return_value = None

        self.service.send_immediate_notifications()

        # Non-important notification
        mock_filter.assert_called_once_with([self.notifications[0]])
        # Immediate notification
        mock_send.assert_called_once_with([self.notifications[1]])
        mock_mark_sent.has_called_with([self.notifications[1]])

    @mock.patch("metabrainz.mail.mark_notifications_sent")
    @mock.patch("metabrainz.mail.get_digest_notifications")
    @mock.patch("metabrainz.mail.NotificationSender._send_notifications")
    def test_send_digest_notifications(self, mock_send, mock_get, mock_mark):
        mock_send.return_value = None
        mock_get.return_value = [self.notifications[0]]
        mock_mark.return_value = None

        self.service.send_digest_notifications()

        mock_get.assert_called_once()
        mock_send.assert_called_once_with([self.notifications[0]])
        mock_mark.assert_called_once_with([self.notifications[0]])

