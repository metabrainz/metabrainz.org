# -*- coding: utf-8 -*-
# DEFAULT CONFIGURATION


# DATABASE
SQLALCHEMY_DATABASE_URI = "postgresql://metabrainz:metabrainz@db:5432/metabrainz"
TEST_SQLALCHEMY_DATABASE_URI = "postgresql://metabrainz_test:metabrainz_test@db:5432/metabrainz_test"
SQLALCHEMY_TRACK_MODIFICATIONS = False


# REPLICATION PACKETS
# Hourly replication packets must be located in this directory. Daily
# replication packets must be located in subdirectory called "daily"
# in REPLICATION_PACKETS_DIR. Weekly packets in subdirectory "weekly".
REPLICATION_PACKETS_DIR = "/data/replication_packets"


# PAYMENTS

PAYMENT_PRODUCTION = False

WEPAY_ACCOUNT_ID = ""
WEPAY_ACCESS_TOKEN = ""

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
SMTP_SERVER = "localhost"
SMTP_PORT = 25

ADMINS = []

RECAPTCHA_PUBLIC_KEY = ""
RECAPTCHA_PRIVATE_KEY = ""

NOTIFICATION_RECIPIENTS = []

PREFERRED_URL_SCHEME = "http"

USE_NGINX_X_ACCEL = True
