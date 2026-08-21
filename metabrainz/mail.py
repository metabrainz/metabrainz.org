"""Application-owned email delivery helpers."""

import smtplib
import socket
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from flask import current_app

SMTP_TIMEOUT = 10


def send_mail(
    subject: str,
    text: str,
    recipients: list[str],
    attachments=None,
    from_name="MetaBrainz Notifications",
    from_addr=None,
    boundary=None,
):
    """Send an email to a list of bare email addresses.

    Keeping display names out of ``recipients`` is intentional: the values are
    also used as SMTP envelope addresses, where ``Name <address>`` is invalid.
    """
    if not isinstance(recipients, list):
        raise ValueError("recipients must be a list of email addresses")

    if "SMTP_SERVER" not in current_app.config or "SMTP_PORT" not in current_app.config:
        raise ValueError("Flask current_app requires config items SMTP_SERVER and SMTP_PORT to be set")

    if attachments is None:
        attachments = []
    if from_addr is None:
        from_addr = "noreply@" + current_app.config["MAIL_FROM_DOMAIN"]

    if current_app.config["TESTING"]:
        return

    if not recipients:
        return

    message = MIMEMultipart(boundary=boundary) if boundary is not None else MIMEMultipart()
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message["From"] = formataddr((from_name, from_addr))
    message.attach(MIMEText(text, _charset="utf-8"))

    for file_obj, subtype, name in attachments:
        attachment = MIMEApplication(file_obj.read(), _subtype=subtype)
        file_obj.close()
        attachment.add_header("content-disposition", "attachment", filename=name)
        message.attach(attachment)

    smtp_server = None
    try:
        smtp_server = smtplib.SMTP(
            current_app.config["SMTP_SERVER"],
            current_app.config["SMTP_PORT"],
            timeout=SMTP_TIMEOUT,
        )
        smtp_server.sendmail(from_addr, recipients, message.as_string())
    except (socket.error, smtplib.SMTPException) as exc:
        current_app.logger.error("Error while sending email: %s", exc, exc_info=True)
        raise MailException(exc) from exc
    finally:
        if smtp_server is not None:
            try:
                smtp_server.quit()
            except (socket.error, smtplib.SMTPException) as exc:
                current_app.logger.warning("Error while closing SMTP connection: %s", exc)


class MailException(Exception):
    """Email delivery failed."""
