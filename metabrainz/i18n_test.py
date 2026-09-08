from unittest import TestCase

from flask import Blueprint, Flask, session

from metabrainz import i18n


class MatchUiLocalesTestCase(TestCase):

    def test_none_or_empty(self):
        self.assertIsNone(i18n.match_ui_locales(None))
        self.assertIsNone(i18n.match_ui_locales(""))

    def test_supported_language(self):
        self.assertEqual(i18n.match_ui_locales("fr"), "fr")
        self.assertEqual(i18n.match_ui_locales("de"), "de")

    def test_primary_subtag_of_regional_tag(self):
        # BCP 47 regional tags fall back to their primary subtag.
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

    def test_regional_catalog_preferred_over_its_base_language(self):
        # A regional catalog must win over its own base language when the
        # client asked for it exactly, rather than being cut down to "pt".
        supported = i18n.SUPPORTED_LANGUAGES
        i18n.SUPPORTED_LANGUAGES = supported + ({"code": "pt_BR", "name": "Português"},)
        try:
            self.assertEqual(i18n.match_ui_locales("pt-BR"), "pt_BR")
            self.assertEqual(i18n.match_ui_locales("pt_BR"), "pt_BR")
        finally:
            i18n.SUPPORTED_LANGUAGES = supported


class GetLocaleTestCase(TestCase):

    def setUp(self):
        # A minimal app is enough: get_locale() only reads the language cookie
        # and the session, so we avoid the heavier DB-backed FlaskTestCase.
        self.app = Flask(__name__)
        self.app.secret_key = "i18n-test"

    def test_default_locale_when_nothing_provided(self):
        with self.app.test_request_context("/"):
            self.assertEqual(i18n.get_locale(), i18n.DEFAULT_LOCALE)

    def test_cookie_takes_precedence(self):
        headers = {"Cookie": f"{i18n.LANGUAGE_COOKIE_NAME}=fr"}
        with self.app.test_request_context("/", headers=headers):
            session[i18n.UI_LOCALE_SESSION_KEY] = "de"
            self.assertEqual(i18n.get_locale(), "fr")

    def test_remembered_ui_locale_used_without_cookie(self):
        with self.app.test_request_context("/"):
            session[i18n.UI_LOCALE_SESSION_KEY] = "de"
            self.assertEqual(i18n.get_locale(), "de")

    def test_remembered_ui_locale_used_when_cookie_unsupported(self):
        headers = {"Cookie": f"{i18n.LANGUAGE_COOKIE_NAME}=zz"}
        with self.app.test_request_context("/", headers=headers):
            session[i18n.UI_LOCALE_SESSION_KEY] = "de"
            self.assertEqual(i18n.get_locale(), "de")

    def test_unsupported_remembered_locale_falls_back_to_default(self):
        # A locale that has since been dropped from SUPPORTED_LANGUAGES must
        # not linger in an old session.
        with self.app.test_request_context("/"):
            session[i18n.UI_LOCALE_SESSION_KEY] = "ja"
            self.assertEqual(i18n.get_locale(), i18n.DEFAULT_LOCALE)

    def test_ui_locales_query_param_alone_does_not_change_locale(self):
        # ui_locales is an OIDC authorization request parameter, not a
        # site-wide language switch: it only takes effect once an OAuth
        # endpoint has recorded it with remember_ui_locales().
        with self.app.test_request_context("/donate?ui_locales=de"):
            self.assertEqual(i18n.get_locale(), i18n.DEFAULT_LOCALE)


class RememberUiLocalesTestCase(TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = "i18n-test"

    def test_supported_hint_is_remembered(self):
        with self.app.test_request_context("/"):
            self.assertEqual(i18n.remember_ui_locales("de-AT fr"), "de")
            self.assertEqual(session[i18n.UI_LOCALE_SESSION_KEY], "de")
            self.assertEqual(i18n.get_locale(), "de")

    def test_unsupported_hint_leaves_the_session_untouched(self):
        with self.app.test_request_context("/"):
            session[i18n.UI_LOCALE_SESSION_KEY] = "fr"
            self.assertIsNone(i18n.remember_ui_locales("ja"))
            self.assertEqual(session[i18n.UI_LOCALE_SESSION_KEY], "fr")

    def test_missing_hint_leaves_the_session_untouched(self):
        with self.app.test_request_context("/"):
            session[i18n.UI_LOCALE_SESSION_KEY] = "fr"
            self.assertIsNone(i18n.remember_ui_locales(None))
            self.assertEqual(session[i18n.UI_LOCALE_SESSION_KEY], "fr")


class SetLanguageTestCase(TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = "i18n-test"
        # set_language falls back to the home page, so that endpoint has to exist.
        index_bp = Blueprint("index", __name__)
        index_bp.add_url_rule("/", "home", lambda: "")
        self.app.register_blueprint(index_bp)
        self.app.register_blueprint(i18n.i18n_bp)
        self.client = self.app.test_client()

    def test_sets_cookie_and_redirects(self):
        response = self.client.get("/set-language/fr?returnto=/donate")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/donate")
        self.assertIn(f"{i18n.LANGUAGE_COOKIE_NAME}=fr", response.headers["Set-Cookie"])

    def test_unsupported_locale_is_rejected(self):
        response = self.client.get("/set-language/ja?returnto=/donate")
        self.assertEqual(response.status_code, 404)

    def test_absolute_url_is_rejected(self):
        response = self.client.get("/set-language/fr?returnto=https://evil.example.com")
        self.assertEqual(response.status_code, 400)

    def test_protocol_relative_url_is_rejected(self):
        response = self.client.get("/set-language/fr?returnto=//evil.example.com")
        self.assertEqual(response.status_code, 400)

    def test_backslash_url_is_rejected(self):
        # Browsers normalise "\" to "/" while parsing a URL, so this would
        # otherwise navigate to //evil.example.com.
        response = self.client.get("/set-language/fr?returnto=/\\evil.example.com")
        self.assertEqual(response.status_code, 400)
        response = self.client.get("/set-language/fr?returnto=\\\\evil.example.com")
        self.assertEqual(response.status_code, 400)
