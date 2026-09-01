from unittest import TestCase

from flask import Flask

from metabrainz import i18n


class MatchUiLocalesTestCase(TestCase):

    def test_none_or_empty(self):
        self.assertIsNone(i18n.match_ui_locales(None))
        self.assertIsNone(i18n.match_ui_locales(""))

    def test_supported_language(self):
        self.assertEqual(i18n.match_ui_locales("fr"), "fr")
        self.assertEqual(i18n.match_ui_locales("de"), "de")

    def test_primary_subtag_of_regional_tag(self):
        # BCP 47 regional tags match on their primary subtag.
        self.assertEqual(i18n.match_ui_locales("fr-CA"), "fr")
        self.assertEqual(i18n.match_ui_locales("es-419"), "es")

    def test_posix_style_separator(self):
        self.assertEqual(i18n.match_ui_locales("fr_FR"), "fr")

    def test_preference_order(self):
        # First supported tag in the ordered list wins.
        self.assertEqual(i18n.match_ui_locales("zh nl fr en"), "fr")

    def test_case_insensitive(self):
        self.assertEqual(i18n.match_ui_locales("FR-ca"), "fr")

    def test_unsupported_returns_none(self):
        self.assertIsNone(i18n.match_ui_locales("zh ja ko"))


class GetLocaleTestCase(TestCase):

    def setUp(self):
        # A minimal app is enough: get_locale() only reads request cookies and
        # args, so we avoid the heavier DB-backed FlaskTestCase.
        self.app = Flask(__name__)

    def test_default_locale_when_nothing_provided(self):
        with self.app.test_request_context("/"):
            self.assertEqual(i18n.get_locale(), i18n.DEFAULT_LOCALE)

    def test_cookie_takes_precedence(self):
        headers = {"Cookie": f"{i18n.LANGUAGE_COOKIE_NAME}=fr"}
        with self.app.test_request_context("/?ui_locales=de", headers=headers):
            self.assertEqual(i18n.get_locale(), "fr")

    def test_ui_locales_used_without_cookie(self):
        with self.app.test_request_context("/?ui_locales=fr-CA"):
            self.assertEqual(i18n.get_locale(), "fr")

    def test_ui_locales_ignored_when_cookie_unsupported(self):
        # An unsupported cookie value falls through to the ui_locales hint.
        headers = {"Cookie": f"{i18n.LANGUAGE_COOKIE_NAME}=zz"}
        with self.app.test_request_context("/?ui_locales=de", headers=headers):
            self.assertEqual(i18n.get_locale(), "de")

    def test_unsupported_ui_locales_falls_back_to_default(self):
        with self.app.test_request_context("/?ui_locales=ja"):
            self.assertEqual(i18n.get_locale(), i18n.DEFAULT_LOCALE)
