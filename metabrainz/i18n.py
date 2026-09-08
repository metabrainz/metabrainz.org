from babel import negotiate_locale
from flask import Blueprint, abort, redirect, request, session, url_for


LANGUAGE_COOKIE_NAME = "lang"
DEFAULT_LOCALE = "en"
# Where a locale negotiated from an OIDC ``ui_locales`` hint is remembered for
# the rest of the browser session, see remember_ui_locales().
UI_LOCALE_SESSION_KEY = "ui_locale"
i18n_bp = Blueprint("i18n", __name__)
SUPPORTED_LANGUAGES = (
    {"code": "en", "name": "English"},
    {"code": "es", "name": "Español"},
    {"code": "fr", "name": "Français"},
    {"code": "de", "name": "Deutsch"},
)


def N_(string):
    """Mark a string for translation without translating it here.

    ``N_`` is one of pybabel's default extraction keywords, so strings wrapped
    in it end up in messages.pot and can be translated later, at a point where
    a request (and therefore an active locale) exists. For example, module level
    strings. lazy_gettext can be used but requires extra handling with pybabel
    and json.dumps.
    """
    return string


def get_supported_locale_codes():
    return [language["code"] for language in SUPPORTED_LANGUAGES]


def match_ui_locales(ui_locales):
    """Return the first supported locale requested via OIDC ``ui_locales``.

    ``ui_locales`` is a space-separated, preference-ordered list of BCP 47
    language tags (e.g. ``"fr-CA fr en"``), as defined by OpenID Connect Core
    1.0 section 3.1.2.1. Returns None if nothing matches.
    """
    if not ui_locales:
        return None

    # negotiate_locale() matches an exact tag first and only then falls back to
    # the primary subtag, so a regional catalog (say pt_BR) is preferred over
    # its base language when both are supported. Both sides are normalised to
    # lowercase and "-" separators because it compares tags verbatim.
    canonical = {code.replace("_", "-").lower(): code for code in get_supported_locale_codes()}
    preferred = [tag.replace("_", "-").lower() for tag in ui_locales.split()]
    matched = negotiate_locale(preferred, list(canonical), sep="-")
    return canonical.get(matched)


def remember_ui_locales(ui_locales):
    """Remember the locale an OAuth client asked for via ``ui_locales``.

    The hint only appears on the authorization request itself, but the pages
    that follow it (sign in, sign up, consent, errors) are separate requests on
    other blueprints, so it is negotiated once here and kept in the session for
    the rest of the flow. The user's own language cookie still wins.
    """
    locale = match_ui_locales(ui_locales)
    if locale:
        session[UI_LOCALE_SESSION_KEY] = locale
    return locale


def get_locale():
    """Return the active locale.

    Precedence:
      1. The user's explicit language cookie (their site-wide choice).
      2. A locale remembered from an OpenID Connect ``ui_locales`` hint sent by
         an OAuth client such as MusicBrainz Picard (section 3.1.2.1), so the
         sign in, consent and error pages of that flow match the client.
      3. The default locale.
    """
    cookie_locale = request.cookies.get(LANGUAGE_COOKIE_NAME)
    if cookie_locale in get_supported_locale_codes():
        return cookie_locale

    ui_locale = session.get(UI_LOCALE_SESSION_KEY)
    if ui_locale in get_supported_locale_codes():
        return ui_locale

    return DEFAULT_LOCALE


@i18n_bp.route("/set-language/<locale>")
def set_language(locale):
    """Set the language cookie and redirect back to the originating page."""
    returnto = request.args.get("returnto", url_for("index.home"))
    if not _is_safe_returnto(returnto):
        abort(400)

    if locale not in get_supported_locale_codes():
        abort(404)

    response = redirect(returnto)
    response.set_cookie(
        LANGUAGE_COOKIE_NAME,
        locale,
        max_age=365 * 24 * 60 * 60,
        httponly=False,
        path="/",
        samesite="Lax",
    )
    return response


def _is_safe_returnto(returnto):
    """Return True if returnto is a path on this site and not a redirect off it.

    Browsers normalise a backslash to a forward slash while parsing a URL (per
    the WHATWG URL standard), so "/\\evil.example.com" is treated as the
    protocol-relative "//evil.example.com" and navigates cross-origin. Reject
    backslashes outright rather than trying to spot every such spelling.
    """
    if not returnto or "\\" in returnto:
        return False
    return returnto.startswith("/") and not returnto.startswith("//")


def get_locale_context():
    """Provide locale variables and helpers to Jinja templates."""
    locale = get_locale()
    return {
        "current_locale": locale,
        "get_language_url": get_language_url,
        "supported_languages": SUPPORTED_LANGUAGES,
    }


def get_language_url(locale):
    # The language switcher is a link, so it can only return the user to a URL
    # that answers GET. A page rendered in response to a POST (the OAuth error
    # page, for one) would answer 405, so send those back to the home page.
    if request.method == "GET":
        returnto = request.full_path.rstrip("?")
    else:
        returnto = url_for("index.home")
    return url_for("i18n.set_language", locale=locale, returnto=returnto)
