# -*- coding: utf-8 -*-
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import current_app
import smtplib


def send_org_signup_notification(values):
    """Send notification about new organization sign up request.

    Args:
        values: List of attributes which describe organization's sign up
        request. Must contain tuples with two values (name, value). Its
        contents will be sent to the recipient of notifications.
    """
    if current_app.config['TESTING']:  # Not sending any emails during the testing process
        return

    from_addr = 'noreply@' + current_app.config['MAIL_FROM_DOMAIN']

    message = MIMEMultipart('mixed')
    message['Subject'] = '[MetaBrainz] New organization signed up'
    message['From'] = "MetaBrainz Notifications <%s>" % from_addr
    message['To'] = '%s <%s>' % (current_app.config['MANAGER_NAME'],
                                 current_app.config['MANAGER_EMAIL'])
    message.attach(MIMEText(pairs_list_to_string(values), _charset='utf-8'))

    server = smtplib.SMTP(current_app.config['SMTP_SERVER'], current_app.config['SMTP_PORT'])
    server.sendmail(from_addr, [current_app.config['MANAGER_EMAIL']], message.as_string())
    server.quit()


def pairs_list_to_string(pairs):
    return '\n'.join([
        '%s: %s' % (pair[0], pair[1]) for pair in pairs
    ])
