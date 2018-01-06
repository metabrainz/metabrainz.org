# -*- coding: utf-8 -*-
# DEFAULT CONFIGURATION

SECRET_KEY = "CHANGE_THIS"


# DATABASE
SQLALCHEMY_DATABASE_URI = "postgresql://metabrainz:metabrainz@db:5432/metabrainz"
SQLALCHEMY_TRACK_MODIFICATIONS = False


# REPLICATION PACKETS
# Hourly replication packets must be located in this directory. Daily
# replication packets must be located in subdirectory called "daily"
# in REPLICATION_PACKETS_DIR. Weekly packets in subdirectory "weekly".
REPLICATION_PACKETS_DIR = "/data/replication_packets"
JSON_DUMPS_DIR = "/data/json_dumps"


# PAYMENTS

PAYMENT_PRODUCTION = False

PAYPAL_ACCOUNT_IDS = {
    "USD": "",
    "EUR": "",
}
PAYPAL_BUSINESS = ""

STRIPE_KEYS = {
    "SECRET": "",
    "PUBLISHABLE": "",
}
STRIPE_TEST_KEYS = {
    "SECRET": "",
    "PUBLISHABLE": "",
}


# REDIS
REDIS = {
    "host": "redis",
    "port": 6379,
    "namespace": "MEB",
}


# MUSICBRAINZ OAUTH

MUSICBRAINZ_BASE_URL = "https://musicbrainz.org/"
MUSICBRAINZ_CLIENT_ID = ""
MUSICBRAINZ_CLIENT_SECRET = ""


# MISC

# Mail server
SMTP_SERVER = "metabrainz-mail"
SMTP_PORT = 25
MAIL_FROM_DOMAIN = "metabrainz.org"

# List of supported UI languages.
# Valid language codes can be obtained from Transifex.
SUPPORTED_LANGUAGES = [
    'en',  # English
    'hr',  # Croatian
    'nl',  # Dutch
    'et',  # Estonian
    'fi',  # Finnish
    'fr',  # French
    'de',  # German
    'it',  # Italian
    'nb',  # Norwegian Bokmål
    'pl',  # Polish
    'es',  # Spanish
    'sv',  # Swedish
    'ru',  # Russian
]

ADMINS = []

RECAPTCHA_PUBLIC_KEY = ""
RECAPTCHA_PRIVATE_KEY = ""

NOTIFICATION_RECIPIENTS = []

USE_COMPILED_STYLING = True

BEHIND_GATEWAY = True
REMOTE_ADDR_HEADER = "X-MB-Remote-Addr"

USE_NGINX_X_ACCEL = False
