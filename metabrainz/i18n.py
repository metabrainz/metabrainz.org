from flask import Blueprint, abort, redirect, request, url_for


LANGUAGE_COOKIE_NAME = "lang"
DEFAULT_LOCALE = "en"
i18n_bp = Blueprint("i18n", __name__)
SUPPORTED_LANGUAGES = (
    {"code": "en", "name": "English"},
    {"code": "es", "name": "Español"},
    {"code": "fr", "name": "Français"},
    {"code": "de", "name": "Deutsch"},
)


def get_supported_locale_codes():
    return [language["code"] for language in SUPPORTED_LANGUAGES]


def match_ui_locales(ui_locales):
    """Return the first supported locale requested via OIDC ``ui_locales``.

    ``ui_locales`` is a space-separated, preference-ordered list of BCP 47
    language tags (e.g. ``"fr-CA fr en"``), as defined by OpenID Connect Core
    1.0 section 3.1.2.1. Matching is done on the primary language subtag
    against the supported locale codes. Returns None if nothing matches.
    """
    if not ui_locales:
        return None
    supported = get_supported_locale_codes()
    for tag in ui_locales.split():
        primary_subtag = tag.replace("_", "-").split("-")[0].lower()
        if primary_subtag in supported:
            return primary_subtag
    return None


def get_locale():
    """Return the active locale.

    Precedence:
      1. The user's explicit language cookie (their site-wide choice).
      2. The OpenID Connect ``ui_locales`` request hint, e.g. from an OAuth
         client such as MusicBrainz Picard (section 3.1.2.1). This lets the
         authorization/consent and error pages match the client's language
         when the user has not set their own preference here.
      3. The default locale.
    """
    cookie_locale = request.cookies.get(LANGUAGE_COOKIE_NAME)
    if cookie_locale in get_supported_locale_codes():
        return cookie_locale

    ui_locale = match_ui_locales(request.args.get("ui_locales"))
    if ui_locale:
        return ui_locale

    return DEFAULT_LOCALE


@i18n_bp.route("/set-language/<locale>")
def set_language(locale):
    """Set the language cookie and redirect back to the originating page."""
    returnto = request.args.get("returnto", url_for("index.home"))
    if not returnto.startswith("/") or returnto.startswith("//"):
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


def get_locale_context():
    """Provide locale variables and helpers to Jinja templates."""
    locale = get_locale()
    return {
        "current_locale": locale,
        "get_language_url": get_language_url,
        "supported_languages": SUPPORTED_LANGUAGES,
    }


def get_language_url(locale):
    return url_for("i18n.set_language", locale=locale, returnto=request.full_path.rstrip("?"))
