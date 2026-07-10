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


def get_locale():
    """Return the active locale from the language cookie"""
    cookie_locale = request.cookies.get(LANGUAGE_COOKIE_NAME)
    if cookie_locale in get_supported_locale_codes():
        return cookie_locale

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
