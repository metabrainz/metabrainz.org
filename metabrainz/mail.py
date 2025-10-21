import uuid
import orjson
import requests
from flask import current_app
from brainzutils import cache
from brainzutils.mail import send_mail

from metabrainz.db.notification import (
    filter_non_digest_notifications,
    get_digest_notifications,
    mark_notifications_sent,
)

FAILED_MAIL_HASH_KEY = "failed_mail"


class NotificationSender:
    def __init__(self, notifications):
        self.notifications = notifications

    def _send_notifications(self, notifications: list[dict]):
        """Helper function to send immediate notifications through mail.
        If sending fails, the notification is stored in cache for later retry.
        """
        for notification in notifications:
            try:
                if notification.get("subject") and notification.get("body"):
                    send_mail(
                        subject=notification["subject"],
                        text=notification["body"],
                        recipients=[notification["recipient"]],
                        from_addr=notification["sent_from"],
                    )
                elif notification.get("template_id") and notification.get("template_params"):
                    self.send_html_mail(
                        from_addr=notification["sent_from"],
                        template_id=notification["template_id"],
                        template_params=notification["template_params"],
                        recipient=notification["recipient"],
                        message_id=notification["email_id"],
                    )

            except Exception as err:
                current_app.logger.error(
                    "Failed to send mail to recipient %s, %s",
                    notification["recipient"],
                    str(err),
                )
                cache.hset(FAILED_MAIL_HASH_KEY, str(uuid.uuid4()), orjson.dumps(notification))

    def send_immediate_notifications(self):
        """Sends notifications that are marked as important or are for users with notifications enabled and digest disabled."""

        immediate_notifications = []
        unimportant_notifications = []

        for notification in self.notifications:
            if notification["important"] and notification["send_email"]:
                immediate_notifications.append(notification)

            elif not notification["important"] and notification["send_email"]:
                unimportant_notifications.append(notification)

        non_digest_notifications = filter_non_digest_notifications(
            unimportant_notifications
        )
        immediate_notifications += non_digest_notifications

        self._send_notifications(immediate_notifications)
        mark_notifications_sent(immediate_notifications)

    def send_digest_notifications(self):
        """Send notifications which have reached their digest_age."""

        notifications = get_digest_notifications()
        self._send_notifications(notifications)
        mark_notifications_sent(notifications)

    def send_html_mail(
        self,
        from_addr: str,
        recipient: str,
        template_id: str,
        template_params: dict,
        language: str | None = None,
        in_reply_to: list[str] | None = [],
        sender: str | None = None,
        references: list[str] | None = [],
        reply_to: str | None = None,
        message_id: str | None = None,
    ):
        """
        Send HTML email through MB mail service.

        Args:
            from_addr (str):
                The email address of the sender.
            recipient (str):
                The email address of the recipient.
            template_id (str):
                MB mail service template id for the required template.
            template_params (dict):
                Dictionary containing the data to be passed into the template.
            language (str) :
                Optional. The language preference of the recipient.
            in_reply_to (list[str]):
                Optional. list of Message ID of the emails thats being replied to.
            sender (str):
                Optional. The address ultimately sending the email Should not be set if same as from address.
            references (list[str]):
                Optional. list of Message ID of the emails that this email references.
            reply_to (str):
                Optional. Reply-To email header.
            message_id (str):
                Optional. UUID for the email.

        Raises:
            HTTPError: If sending email fails.
        """

        single_mail_endpoint = current_app.config["MB_MAIL_SERVER_URI"] + "/send_single"
        data = {
            "from": from_addr,
            "to": recipient,
            "template_id": template_id,
            "params": template_params,
            "language": language,
            "in_reply_to": in_reply_to,
            "sender": sender,
            "references": references,
            "reply_to": reply_to,
            "message_id": message_id,
        }

        response = requests.post(url=single_mail_endpoint, json=data)
        response.raise_for_status()
