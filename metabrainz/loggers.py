import logging
from logging.handlers import SMTPHandler


def add_email_handler(app):
    """Adds email notifications."""
    mail_handler = SMTPHandler(
        (app.config['SMTP_SERVER'], app.config['SMTP_PORT']),
        'no-reply@' + app.config['MAIL_FROM_DOMAIN'],
        app.config['LOG_RECIPIENTS'],
        app.config['LOG_EMAIL_TOPIC']
    )
    mail_handler.setLevel(logging.ERROR)

    mail_handler.setFormatter(logging.Formatter('''
    Message type: %(levelname)s
    Location: %(pathname)s:%(lineno)d
    Module: %(module)s
    Function: %(funcName)s
    Time: %(asctime)s
    Message:
    %(message)s
    '''))

    app.logger.addHandler(mail_handler)
