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


# PAYMENTS

PAYMENT_PRODUCTION = False

PAYPAL_PRIMARY_EMAIL = ""
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

ADMINS = []

RECAPTCHA_PUBLIC_KEY = ""
RECAPTCHA_PRIVATE_KEY = ""

NOTIFICATION_RECIPIENTS = []

USE_COMPILED_STYLING = True

BEHIND_GATEWAY = True
REMOTE_ADDR_HEADER = "X-MB-Remote-Addr"

USE_NGINX_X_ACCEL = False
