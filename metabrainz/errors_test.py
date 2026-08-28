from unittest import TestCase

from flask import Flask
from flask_babel import Babel

from metabrainz import errors


class OAuthErrorMessageTestCase(TestCase):

    def setUp(self):
        # A minimal app with Babel is enough: _oauth_error_message only calls
        # gettext, so we avoid the heavier DB-backed FlaskTestCase.
        self.app = Flask(__name__)
        Babel(self.app)

    def test_known_codes_return_a_message(self):
        known = [
            "access_denied",
            "invalid_request",
            "invalid_client",
            "invalid_grant",
            "unauthorized_client",
            "unsupported_response_type",
            "unsupported_grant_type",
            "invalid_scope",
            "server_error",
            "temporarily_unavailable",
            "interaction_required",
            "login_required",
            "consent_required",
            "account_selection_required",
        ]
        with self.app.test_request_context("/"):
            for code in known:
                message = errors._oauth_error_message(code)
                self.assertTrue(message, f"expected a message for {code!r}")
                # The user-facing message must not be the raw error code.
                self.assertNotEqual(message, code)

    def test_unknown_code_returns_none(self):
        with self.app.test_request_context("/"):
            self.assertIsNone(errors._oauth_error_message("some_new_code"))

    def test_none_code_returns_none(self):
        with self.app.test_request_context("/"):
            self.assertIsNone(errors._oauth_error_message(None))
