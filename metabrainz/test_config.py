DEBUG = False
TESTING = True
SECRET_KEY = "test"
WTF_CSRF_ENABLED = False
DEBUG_TB_INTERCEPT_REDIRECTS = False

PAYMENT_PRODUCTION = False  # set to False to use testing environments for donations

SQLALCHEMY_DATABASE_URI = "postgresql://metabrainz:metabrainz@db_test:5432/metabrainz"

# PayPal
PAYPAL_ACCOUNT_IDS = {
    "USD": "paypal-usd@example.org",
    "EUR": "paypal-eur@example.org",
}
PAYPAL_BUSINESS = "payment@example.org"

# Stripe
STRIPE_KEYS = {
    "SECRET": "",
    "PUBLISHABLE": "",
}
STRIPE_TEST_KEYS = {
    "SECRET": "",
    "PUBLISHABLE": "",
}

REDIS = {
    "host": "redis",
    "port": 6379,
    "namespace": "MEB",
}

# Logging
LOG_FILE = None
LOG_EMAIL = None
LOG_SENTRY = None

# MusicBrainz
MUSICBRAINZ_BASE_URL = "https://musicbrainz.org/"
MUSICBRAINZ_CLIENT_ID = ""
MUSICBRAINZ_CLIENT_SECRET = ""

ADMINS = []

# reCAPTCHA
RECAPTCHA_PUBLIC_KEY = ""
RECAPTCHA_PRIVATE_KEY = ""

# List of email addresses
NOTIFICATION_RECIPIENTS = []

BEHIND_GATEWAY = False

MAIL_FROM_DOMAIN = "example.org"
