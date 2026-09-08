import importlib
import pkgutil
from unittest import TestCase

import authlib
from authlib.oauth2 import OAuth2Error
from flask import Flask
from flask_babel import Babel

from metabrainz import errors
from metabrainz.errors import OAUTH_ERROR_MESSAGES


def authlib_error_codes():
    """Every error code declared by an OAuth2Error subclass shipped by authlib."""
    for module in pkgutil.walk_packages(authlib.__path__, prefix="authlib."):
        try:
            importlib.import_module(module.name)
        except Exception:
            # Integrations for web frameworks this project does not install.
            continue

    codes, pending = set(), [OAuth2Error]
    while pending:
        error_class = pending.pop()
        code = getattr(error_class, "error", None)
        if code:
            codes.add(code)
        pending.extend(error_class.__subclasses__())
    return codes


class OAuthErrorMessageTestCase(TestCase):

    def setUp(self):
        # A minimal app with Babel is enough: oauth_error_message only calls
        # gettext, so we avoid the heavier DB-backed FlaskTestCase.
        self.app = Flask(__name__)
        Babel(self.app)

    def test_unknown_code_returns_none(self):
        with self.app.test_request_context("/"):
            self.assertIsNone(errors.oauth_error_message("some_new_code"))

    def test_none_code_returns_none(self):
        with self.app.test_request_context("/"):
            self.assertIsNone(errors.oauth_error_message(None))

    def test_known_code_returns_its_message(self):
        with self.app.test_request_context("/"):
            self.assertEqual(
                errors.oauth_error_message("access_denied"),
                OAUTH_ERROR_MESSAGES["access_denied"],
            )

    def test_error_codes_are_known_to_authlib(self):
        """Guard against entries for errors nothing can raise.

        An unreachable code is a string every translator has to translate for a
        page that can never be shown.
        """
        known = authlib_error_codes()
        for code in OAUTH_ERROR_MESSAGES:
            self.assertIn(code, known)
