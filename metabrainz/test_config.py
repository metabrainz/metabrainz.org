DEBUG = False
TESTING = True
SECRET_KEY = "test"
WTF_CSRF_ENABLED = False
DEBUG_TB_INTERCEPT_REDIRECTS = False

PAYMENT_PRODUCTION = False  # set to False to use testing environments for donations

# PayPal
PAYPAL_PRIMARY_EMAIL = "paypal@example.org"
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
