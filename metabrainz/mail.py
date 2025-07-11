import uuid
from flask import current_app
from typing import List
from brainzutils import cache
from brainzutils.mail import send_mail
from metabrainz.db.notification import filter_non_digest_notifications

FAILED_MAIL_HASH_KEY = "failed_mail"


class NotificationSender:
    def __init__(self, notifications):
        self.notifications = notifications

    def _send_notifications_batch(self, notifications: List[dict]):
        """Helper function to send immediate notifications through mail.
        If sending fails, the notification is stored in cache for later retry.
        """
        for notification in notifications:
            try:
                send_mail(
                    subject=notification["subject"],
                    text=notification["body"],
                    recipients=[notification["to"]],
                    from_addr=notification["sent_from"],
                )
            except Exception as err:
                current_app.logger.error(
                    "Failed to send mail to recipient %s, %s",
                    notification["to"],
                    str(err),
                )
                cache.hset(FAILED_MAIL_HASH_KEY, str(uuid.uuid4()), notification)

    def send_immediate_notifications(self):
        """Sends notifications that are marked as important or are for users with digest disabled."""

        immediate_notifications = []
        unimportant_notifications = []

        for notification in self.notifications:
            if notification["important"] and notification["send_email"]:
                if notification.get("subject") and notification.get("body"):
                    immediate_notifications.append(notification)
                else:
                    pass  # TODO: integrate mb-mail

            elif not notification["important"] and notification["send_email"]:
                unimportant_notifications.append(notification)

        non_digest_notifications = filter_non_digest_notifications(
            unimportant_notifications
        )
        immediate_notifications += non_digest_notifications

        self._send_notifications_batch(immediate_notifications)
