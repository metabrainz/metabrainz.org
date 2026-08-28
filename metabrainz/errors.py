import json

from authlib.oauth2 import OAuth2Error
from flask import render_template
from flask_babel import gettext


def _oauth_error_message(code):
    """Return a translated, user-facing message for an OAuth error code.

    OAuth/OIDC error *codes* (e.g. ``access_denied``) are stable ASCII tokens,
    so they can be safely translated, unlike ``error_description`` which is a
    developer-facing, ASCII-only field per RFC 6749 section 4.1.2.1. Unknown
    codes return None so the caller can fall back to the raw description.

    See RFC 6749 sections 4.1.2.1 and 5.2, and OpenID Connect Core 1.0
    section 3.1.2.6 for the error codes handled here.
    """
    # Built at request time so translations reflect the active locale.
    messages = {
        "access_denied": gettext("Authorization was declined."),
        "invalid_request": gettext("The authorization request was invalid."),
        "invalid_client": gettext("The application could not be authenticated."),
        "invalid_grant": gettext("The authorization has expired or is no longer valid."),
        "unauthorized_client": gettext("This application is not allowed to request authorization."),
        "unsupported_response_type": gettext("The authorization request is not supported."),
        "unsupported_grant_type": gettext("The authorization request is not supported."),
        "invalid_scope": gettext("The requested permissions are invalid."),
        "server_error": gettext("The server encountered an error. Please try again later."),
        "temporarily_unavailable": gettext("The service is temporarily unavailable. Please try again later."),
        "interaction_required": gettext("Additional interaction is required to sign in."),
        "login_required": gettext("You need to sign in to continue."),
        "consent_required": gettext("Your consent is required to continue."),
        "account_selection_required": gettext("You need to select an account to continue."),
    }
    return messages.get(code)


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
                # developer-facing description.
                "message": _oauth_error_message(error.error),
            }
        }))
