import logging
from logging.handlers import SMTPHandler


def add_email_handler(app):
    """Adds email notifications."""
    credentials = None
    if 'MAIL_USERNAME' in app.config or 'MAIL_PASSWORD' in app.config:
        credentials = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
    mail_handler = SMTPHandler(
        (app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
        app.config['MAIL_FROM_ADDR'],
        app.config['LOG_RECIPIENTS'],
        app.config['LOG_EMAIL_TOPIC'],
        credentials)
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
