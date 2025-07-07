import uuid
from flask import current_app
from brainzutils import cache
from brainzutils.mail import send_mail

FAILED_MAIL_HASH_KEY = "failed_mail"


class NotificationSender:
    def __init__(self, notifications):
        self.notifications = notifications

    def _send_mail(self, notification):
        """Helper function to send a notification through mail.
        If sending fails, the notification is stored in cache for later retry.
        """
        try:
            send_mail(
                subject=notification["subject"],
                text=notification["body"],
                recipients=[notification["to"]],
                from_addr=notification["sent_from"],
            )
        except Exception as err:
            current_app.logger.error(
                "Failed to send mail to recipient %s, %s", notification["to"], str(err)
            )
            cache.hset(FAILED_MAIL_HASH_KEY, str(uuid.uuid4()), notification)

    def send_important_notifications(self):
        """Sends all the important notifications."""
        for notif in self.notifications:
            if notif["important"] and notif["send_email"]:
                if notif.get("subject") and notif.get("body"):
                    self._send_mail(notif)
                else:
                    pass  # TODO: integrate mb-mail
