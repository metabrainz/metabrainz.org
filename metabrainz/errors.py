import json

from authlib.oauth2 import OAuth2Error
from flask import render_template
from flask_babel import gettext

from metabrainz.i18n import N_

# User-facing messages keyed by the OAuth/OIDC error *code*. Codes (e.g.
# ``access_denied``) are stable ASCII tokens, so they can be translated, unlike
# ``error_description``, which is a developer-facing, ASCII-only field per RFC
# 6749 section 4.1.2.1.
#
# Only codes that can actually reach this handler are listed: it renders HTML
# for the authorization endpoint, and authlib handles token endpoint errors
# (invalid_grant, unsupported_grant_type, ...) internally, never letting them
# escape as an exception. Unlisted codes fall back to the generic message in
# the client, so an unreachable entry is only a string translators must
# needlessly translate. test_error_codes_are_known_to_authlib guards this.
#
# See RFC 6749 sections 4.1.2.1 and 5.2, and OpenID Connect Core 1.0
# section 3.1.2.6 for the error codes handled here.
OAUTH_ERROR_MESSAGES = {
    "access_denied": N_("Authorization was declined."),
    "invalid_request": N_("The authorization request was invalid."),
    "invalid_client": N_("The application could not be authenticated."),
    "unauthorized_client": N_("This application is not allowed to request authorization."),
    "unsupported_response_type": N_("The application asked for a response type this server does not support."),
    "invalid_scope": N_("The permissions requested by the application are invalid."),
    "login_required": N_("You need to sign in to continue."),
    "consent_required": N_("Your consent is required to continue."),
}


def oauth_error_message(code):
    """Return a translated, user-facing message for an OAuth error code.

    Unknown codes return None so the caller can fall back to a generic message.
    """
    message = OAUTH_ERROR_MESSAGES.get(code)
    return gettext(message) if message else None


def init_error_handlers(app):

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("errors/400.html", error=error), 400

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html", error=error), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html", error=error), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template("errors/500.html", error=error), 500

    @app.errorhandler(503)
    def service_unavailable(error):
        return render_template("errors/503.html", error=error), 503

    @app.errorhandler(OAuth2Error)
    def oauth_error_handler(error: OAuth2Error):
        return render_template("oauth/error.html", props=json.dumps({
            "error": {
                "name": error.error,
                "description": error.get_error_description(),
                # Translated, user-facing message chosen by the stable error
                # code; None for unknown codes so the client falls back to the
                # generic translated message.
                "message": oauth_error_message(error.error),
            }
        }))
