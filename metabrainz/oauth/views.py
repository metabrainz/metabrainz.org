import json
from datetime import datetime, timezone
from functools import wraps
from urllib.parse import urljoin

from authlib.oauth2.rfc6749 import InvalidRequestError, OAuth2Error, scope_to_list
from flask import Blueprint, request, render_template, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from flask_wtf.csrf import generate_csrf
from psycopg2.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError

from metabrainz.decorators import nocache, crossdomain
from metabrainz.i18n import get_supported_locale_codes, remember_ui_locales
from metabrainz.model import db, OAuth2Scope, get_scopes, OAuth2AccessToken
from metabrainz.model.oauth.base_token import create_tokens
from metabrainz.model.oauth.client import OAuth2ClientPrivilege
from metabrainz.model.oauth.provisioned_user import OAuth2ProvisionedUser
from metabrainz.model.user import User, UsernameNotAllowedException
from metabrainz.model.webhook import EVENT_USER_CREATED, EVENT_USER_UPDATED
from metabrainz.oauth.authorization_server import authorization_server
from metabrainz.oauth.forms import AuthorizationForm
from metabrainz.oauth.oidc_grant import build_user_info
from metabrainz.oauth.scopes import scope_description
from metabrainz.user.email import send_welcome_email
from metabrainz.user.rate_limit import check_registration_request_rate_limit, increment_registration_request_count
from metabrainz.user.registration import (
    validate_registration_email,
    validate_registration_username,
)
from metabrainz.utils import build_url

oauth2_bp = Blueprint("oauth2", __name__)
wellknown_bp = Blueprint("well-known", __name__)


@oauth2_bp.before_request
def before_oauth2_request():
    """Remember the client's ``ui_locales`` hint for the rest of the flow.

    This runs before the view, and so before @login_required can redirect an
    anonymous user to the sign in or sign up page, where the hint is no longer
    part of the query string.
    """
    remember_ui_locales(request.args.get("ui_locales"))


@oauth2_bp.after_request
def after_oauth2_request(response):
    """ Add security headers for Referrer-Policy, Content-Security-Policy, Cache-Control and X-Frame-Options """
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    # todo: add content-security-policy headers
    return response


def _oauth_error(error: str, description: str, status_code: int = 400, headers=None):
    response = jsonify({
        "error": error,
        "error_description": description,
    })
    response.status_code = status_code
    for key, value in headers or []:
        response.headers.add(key, value)
    return response


def _authlib_oauth_error(error: OAuth2Error):
    return _oauth_error(
        error.error,
        error.description or error.get_error_description(),
        error.status_code,
        error.get_headers(),
    )


def _authenticate_registration_request_client():
    try:
        oauth_request = authorization_server.create_oauth2_request(request)
        client = authorization_server.authenticate_client(
            oauth_request,
            ["client_secret_basic"],
            endpoint="registration_request",
        )
    except OAuth2Error as error:
        return None, _authlib_oauth_error(error)

    if not client.has_privilege(OAuth2ClientPrivilege.REGISTRATION_REQUEST):
        return None, _oauth_error(
            "unauthorized_client",
            "The client is not authorized to create registration requests.",
            403,
        )

    return client, None


REGISTRATION_REQUEST_USERNAME_ERRORS = {
    "missing_username": "Missing 'username' in request.",
    "invalid_username": "Invalid 'username' in request.",
    "username_taken": "The requested username is already in use.",
    "username_not_allowed": "The requested username is not allowed.",
}

REGISTRATION_REQUEST_EMAIL_ERRORS = {
    "missing_email": "Missing 'email' in request.",
    "invalid_email": "Invalid 'email' in request.",
    "domain_blacklisted": "Registration from this email domain is not allowed.",
    "email_taken": "The requested email is already in use.",
}


def _registration_request_email_confirmed(data):
    if "email_confirmed" not in data:
        return False, None

    value = data.get("email_confirmed")
    if isinstance(value, bool):
        return value, None

    return None, _oauth_error(
        "invalid_request",
        "Invalid 'email_confirmed' in request; expected a boolean.",
    )


def _registration_request_scope(data, client):
    if "scope" not in data:
        return None, None

    scope = data.get("scope")
    if not isinstance(scope, str):
        return None, _oauth_error(
            "invalid_request",
            "Invalid 'scope' in request; expected a space-separated string.",
        )

    scopes = scope_to_list(scope) or []
    scope = " ".join(scopes)
    try:
        authorization_server.validate_requested_scope(scope)
    except OAuth2Error as error:
        return None, _authlib_oauth_error(error)

    # the token is generated here directly, without the OIDC extension and without
    # a nonce to bind it to, so the response cannot carry the id_token that openid
    # promises.
    if "openid" in scopes:
        return None, _oauth_error(
            "invalid_scope",
            "The 'openid' scope cannot be requested at this endpoint; it does not issue ID tokens.",
        )

    disallowed = client.disallowed_scopes(scope)
    if disallowed:
        return None, _oauth_error(
            "invalid_scope",
            "The client is not allowed to request the following scopes: "
            + ", ".join(disallowed),
        )

    return scope, None


def _registration_request_user_details(data):
    username_value = data.get("username")
    if username_value is not None and not isinstance(username_value, str):
        return None, _oauth_error(
            "invalid_request",
            REGISTRATION_REQUEST_USERNAME_ERRORS["invalid_username"],
        )

    username, username_error = validate_registration_username(username_value)
    if username_error:
        return None, _oauth_error("invalid_request", REGISTRATION_REQUEST_USERNAME_ERRORS[username_error])

    email_value = data.get("email")
    if email_value is not None and not isinstance(email_value, str):
        return None, _oauth_error(
            "invalid_request",
            REGISTRATION_REQUEST_EMAIL_ERRORS["invalid_email"],
        )

    email, email_error = validate_registration_email(email_value)
    if email_error:
        return None, _oauth_error("invalid_request", REGISTRATION_REQUEST_EMAIL_ERRORS[email_error])

    email_confirmed, error = _registration_request_email_confirmed(data)
    if error is not None:
        return None, error

    return {
        "username": username,
        "email": email,
        "email_confirmed": email_confirmed,
    }, None


def _json_errors(view):
    """Answer in JSON however the view fails."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except OAuth2Error as error:
            db.session.rollback()
            return _authlib_oauth_error(error)
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Unhandled error in %s", view.__name__)
            return _oauth_error("server_error", "The request could not be completed.", 500)

    return wrapper


def _discard_provisioned_account(user):
    """Undo a provisioning whose welcome email could not be delivered.

    The tokens go with the user: the foreign keys onto "user" cascade, so deleting
    the row takes the access and refresh tokens issued alongside it.
    """
    try:
        db.session.delete(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Could not discard the provisioned account %s after its welcome email failed",
            user.id,
        )


@oauth2_bp.route("/registration-requests", methods=["POST"])
@nocache
@_json_errors
def create_oauth_registration_request():
    """Provision a user account and email them a link to choose a password."""
    client, error = _authenticate_registration_request_client()
    if error is not None:
        return error

    # The allowance is per client, not per IP.
    if check_registration_request_rate_limit(client.id):
        return _oauth_error(
            "access_denied",
            "The client has provisioned too many accounts today. Please try again tomorrow.",
            429,
        )

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _oauth_error(
            "invalid_request",
            "Request body must be a JSON object.",
        )

    scope, error = _registration_request_scope(data, client)
    if error is not None:
        return error

    user_details, error = _registration_request_user_details(data)
    if error is not None:
        return error

    token = None
    scopes = []
    confirmed_at = None
    try:
        if User.email_in_use(user_details["email"]):
            db.session.rollback()
            return _oauth_error("invalid_request", REGISTRATION_REQUEST_EMAIL_ERRORS["email_taken"])

        user = User.add(
            name=user_details["username"],
            unconfirmed_email=user_details["email"],
            password=None,
        )
        if user_details["email_confirmed"]:
            confirmed_at = datetime.now(timezone.utc)
            user.email = user.unconfirmed_email
            user.unconfirmed_email = None
            user.email_confirmed_at = confirmed_at
            user.last_updated = confirmed_at

        db.session.flush()

        db.session.add(OAuth2ProvisionedUser(user_id=user.id, client_id=client.id))
        if scope is not None:
            token = authorization_server.generate_token(
                grant_type="authorization_code",
                client=client,
                user=user,
                scope=scope,
                include_refresh_token=True,
            )
            scopes = get_scopes(db.session, scope)
            create_tokens(
                client_id=client.id,
                user_id=user.id,
                token_data=token,
                access_token_scopes=scopes,
                refresh_token=token["refresh_token"],
                refresh_token_scopes=scopes,
                provisioned=True,
            )
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        if (
            isinstance(error.orig, UniqueViolation)
            and error.orig.diag.constraint_name == "user_name_unq_idx"
        ):
            return _oauth_error(
                "invalid_request",
                REGISTRATION_REQUEST_USERNAME_ERRORS["username_taken"],
            )
        current_app.logger.exception("Error provisioning a user from a registration request")
        return _oauth_error("server_error", "The account could not be created.", 500)
    except UsernameNotAllowedException:
        # the name can be retired between validating it and inserting the row
        db.session.rollback()
        return _oauth_error(
            "invalid_request",
            REGISTRATION_REQUEST_USERNAME_ERRORS["username_not_allowed"],
        )
    except OAuth2Error as error:
        # a restricted scope can be withdrawn from the client between validating the
        # request and minting the token
        db.session.rollback()
        return _authlib_oauth_error(error)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Error provisioning a user from a registration request")
        return _oauth_error("server_error", "The account could not be created.", 500)

    try:
        send_welcome_email(
            user,
            oauth_client_name=client.name,
            oauth_client_description=client.description,
            granted_scopes=[{
                "name": granted_scope.name,
                "description": scope_description(granted_scope),
            } for granted_scope in scopes],
        )
    except Exception:
        current_app.logger.exception(
            "Error sending the welcome email for provisioned user %s", user.id
        )
        _discard_provisioned_account(user)
        return _oauth_error(
            "server_error",
            "The welcome email could not be sent, so the account was not created.",
            500,
        )

    increment_registration_request_count(client.id)

    response = {
        "user_id": user.id,
        "username": user.name,
        "email": user.get_email_any(),
        "email_confirmed": user.is_email_confirmed(),
    }

    user.emit_event(EVENT_USER_CREATED)
    if confirmed_at is not None:
        user.emit_event(
            EVENT_USER_UPDATED,
            old={"email": None},
            new={"email": user.email},
            updated_at=confirmed_at.isoformat(),
        )

    if token is not None:
        response.update(token)
    return jsonify(response), 201


def _access_denied_url(redirect_uri, state):
    """ Build the redirect URI the user is sent to when they deny the authorization request.

    The state parameter, if the client sent one, must be echoed back in the error response
    (RFC 6749 section 4.1.2.1) so the client can correlate it with its original request.
    """
    params = {"error": "access_denied"}
    if state:
        params["state"] = state
    return build_url(redirect_uri, params)


@oauth2_bp.route("/authorize", methods=["GET"])
@login_required
def authorize():
    """ OAuth 2.0 authorization endpoint. """
    grant = authorization_server.get_consent_grant(end_user=current_user)
    scopes = get_scopes(db.session, grant.request.payload.scope)

    approval = grant.request.payload.data.get("approval_prompt", "auto")
    if approval not in {"auto", "force"}:
        raise InvalidRequestError(description="Invalid 'approval_prompt' in request.")

    # TODO: decide if auto approval should revoke existing tokens issued to the same client for the given user
    #   if not improve UI for approved applications in the user page.
    # do not auto approve consent for implicit grant (https://datatracker.ietf.org/doc/html/rfc6819#section-5.2.3.2)
    if approval == "auto" and grant.request.payload.response_type == "code" \
            and grant.client.check_already_approved(current_user.id, scopes):
        return authorization_server.create_authorization_response(grant_user=current_user)

    submission_url = build_url(url_for(".confirm_authorization", _external=False), grant.request.payload.data)
    cancel_url = _access_denied_url(
        grant.request.payload.data.get("redirect_uri"),
        grant.request.payload.data.get("state"),
    )
    return render_template("oauth/prompt.html", props=json.dumps({
        "client_name": grant.client.name,
        "scopes": [{
            "name": scope.name,
            "description": scope_description(scope)
        } for scope in scopes],
        "cancel_url": cancel_url,
        "csrf_token": generate_csrf(),
        "submission_url": submission_url
    }))


@oauth2_bp.route("/authorize/confirm", methods=["POST"])
@login_required
def confirm_authorization():
    form = AuthorizationForm()
    if form.validate_on_submit():
        return authorization_server.create_authorization_response(grant_user=current_user)

    redirect_uri = request.args.get("redirect_uri")
    if not redirect_uri:
        raise InvalidRequestError(description="Missing 'redirect_uri' in request.")
    cancel_url = _access_denied_url(redirect_uri, request.args.get("state"))
    return redirect(cancel_url)


@oauth2_bp.route("/token", methods=["POST"])
@nocache
@crossdomain()
def oauth_token_handler():
    return authorization_server.create_token_response()


@oauth2_bp.route("/revoke", methods=["POST"])
def revoke():
    return authorization_server.create_endpoint_response("revocation")


@oauth2_bp.route("/userinfo", methods=["GET", "POST"])
def user_info():
    # todo: make this OpenID compliant
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "missing auth header"}), 401
    try:
        token = auth_header.split(" ")[1]
    except (ValueError, KeyError):
        return jsonify({"error": "invalid auth header"}), 401

    token = db.session \
        .query(OAuth2AccessToken) \
        .filter_by(access_token=token) \
        .first()

    if token is None:
        return jsonify({"error": "invalid access token"}), 403

    if token.is_expired() or token.is_revoked():
        return jsonify({"error": "expired access token"}), 403

    if token.user_id is None:
        return jsonify({"error": "access token not associated with a user"}), 400

    user = User.get(id=token.user_id)

    return build_user_info(user, token.get_scope(), include_member_since=True)


@oauth2_bp.route("/introspect", methods=["POST"])
def introspect_token():
    return authorization_server.create_endpoint_response("introspection")


@oauth2_bp.route("/health")
def health():
    """Health check endpoint for HAProxy internal gateway."""
    return "OK", 200


def split_by_crlf(s):
    return [v for v in s.splitlines() if v]


@wellknown_bp.route("/jwks.json")
def jwks_uri():
    return {
        "keys": [
            current_app.config["OIDC_JWT_PUBLIC_KEY"]
        ]
    }


@wellknown_bp.route("/openid-configuration", methods=["GET"])
def well_known_oauth_authorization_server():
    # restricted scopes are only available to the clients they have been granted to,
    # so they are left out of the publicly advertised metadata
    scopes = [
        s[0] for s in db.session
        .query(OAuth2Scope.name)
        .filter(OAuth2Scope.restricted.is_(False))
        .all()
    ]
    server = current_app.config["SERVER_BASE_URL"]
    url_prefix = urljoin(server, current_app.config["OAUTH2_BLUEPRINT_PREFIX"])
    # The JWKS and discovery routes live on the well-known blueprint, which is
    # mounted at the site root ("/.well-known"), not under the OAuth2 prefix.
    jwks_uri = urljoin(server, "/.well-known/jwks.json")
    return {
        "issuer": "https://metabrainz.org",
        "authorization_endpoint": f"{url_prefix}/authorize",
        "token_endpoint": f"{url_prefix}/token",
        "userinfo_endpoint": f"{url_prefix}/userinfo",
        "jwks_uri": jwks_uri,
        "scopes_supported": scopes,
        "response_types_supported": ["code", "id_token token", "id_token"],
        "response_modes_supported": ["query", "fragment", "form_post"],
        "grant_types_supported": ["authorization_code", "refresh_token", "implicit"],
        "id_token_signing_alg_values_supported": ["ES256", "none"],
        "subject_types_supported": ["public"],
        "ui_locales_supported": get_supported_locale_codes(),
    }
