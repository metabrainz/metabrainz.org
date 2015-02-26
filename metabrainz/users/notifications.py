# -*- coding: utf-8 -*-
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import current_app
from metabrainz.model.tier import Tier
import smtplib


def send_user_signup_notification(user):
    """Send notification about new signed up user."""
    if current_app.config['TESTING']:  # Not sending any emails during the testing process
        return

    from_addr = 'noreply@' + current_app.config['MAIL_FROM_DOMAIN']

    message = MIMEMultipart('mixed')
    message['Subject'] = '[MetaBrainz] New user signed up'
    message['From'] = "MetaBrainz Notifications <%s>" % from_addr
    message['To'] = '%s <%s>' % (current_app.config['MANAGER_NAME'],
                                 current_app.config['MANAGER_EMAIL'])
    message.attach(MIMEText(pairs_list_to_string([
        ('Organization name', user.org_name),
        ('Contact name', user.contact_name),
        ('Contact email', user.contact_email),

        ('Website URL', user.website_url),
        ('Logo image URL', user.org_logo_url),
        ('API URL', user.api_url),

        ('Street', user.address_street),
        ('City', user.address_city),
        ('State', user.address_state),
        ('Postal code', user.address_postcode),
        ('Country', user.address_country),

        ('Tier', '#%s - %s' % (user.tier_id, Tier.get(id=user.tier_id))),
        ('Payment method', user.payment_method),

        ('Usage description', user.description),
    ]), _charset='utf-8'))

    server = smtplib.SMTP(current_app.config['SMTP_SERVER'], current_app.config['SMTP_PORT'])
    server.sendmail(from_addr, [current_app.config['MANAGER_EMAIL']], message.as_string())
    server.quit()


def pairs_list_to_string(pairs_list):
    return '\n'.join([
        '%s: %s' % (pair[0], pair[1]) for pair in pairs_list
    ])
