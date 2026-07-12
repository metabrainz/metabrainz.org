import json
from urllib.parse import urljoin

from authlib.oauth2.rfc6749 import InvalidRequestError, OAuth2Error
from flask import Blueprint, request, render_template, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from flask_wtf.csrf import generate_csrf

from metabrainz.decorators import nocache, crossdomain
from metabrainz.model import db, OAuth2Scope, get_scopes, OAuth2AccessToken
from metabrainz.model.user import User
from metabrainz.oauth.authorization_server import authorization_server
from metabrainz.oauth.forms import AuthorizationForm
from metabrainz.oauth.registration_request import (
    create_registration_request,
    delete_registration_request,
    get_registration_request,
)
from metabrainz.user.registration import validate_registration_email, validate_registration_username
from metabrainz.utils import build_url

oauth2_bp = Blueprint("oauth2", __name__)
wellknown_bp = Blueprint("well-known", __name__)

REGISTRATION_REQUEST_AUTHORIZE_KEYS = {
    "client_id",
    "response_type",
    "scope",
    "state",
    "redirect_uri",
    "code_challenge",
    "code_challenge_method",
    "nonce",
    "response_mode",
}
REGISTRATION_REQUEST_STORED_AUTHORIZE_KEYS = REGISTRATION_REQUEST_AUTHORIZE_KEYS | {
    "approval_prompt",
    "login_hint",
}


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
            ["client_secret_basic", "client_secret_post"],
            endpoint="registration_request",
        )
    except OAuth2Error as error:
        return None, _authlib_oauth_error(error)

    allowed_clients = current_app.config.get("OAUTH2_REGISTRATION_REQUEST_CLIENTS", [])
    if client.client_id not in allowed_clients:
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


def _registration_request_hints(data):
    username, username_error = validate_registration_username(data.get("username"))
    if username_error:
        return None, _oauth_error("invalid_request", REGISTRATION_REQUEST_USERNAME_ERRORS[username_error])

    email, email_error = validate_registration_email(data.get("email"))
    if email_error:
        return None, _oauth_error("invalid_request", REGISTRATION_REQUEST_EMAIL_ERRORS[email_error])

    return {
        "username": username,
        "email": email,
    }, None


def _preflight_authorization_request(authorize_params):
    authorize_url = build_url(url_for(".authorize", _external=False), authorize_params)
    with current_app.test_request_context(
        authorize_url,
        method="GET",
        base_url=request.url_root,
    ):
        authorization_server.get_consent_grant()


def _validate_registration_request(data, client):
    response_type = data.get("response_type", "code")
    if response_type != "code":
        return None, _oauth_error(
            "unsupported_response_type",
            "Only authorization code registration requests are supported.",
        )

    if not data.get("state"):
        return None, _oauth_error("invalid_request", "Missing 'state' in request.")

    if not data.get("code_challenge"):
        return None, _oauth_error("invalid_request", "Missing 'code_challenge' in request.")

    authorize_params = {}
    for key in REGISTRATION_REQUEST_AUTHORIZE_KEYS:
        value = data.get(key)
        if value is not None:
            authorize_params[key] = value
    authorize_params["client_id"] = client.client_id
    authorize_params["response_type"] = "code"
    authorize_params.setdefault("code_challenge_method", "plain")
    authorize_params["approval_prompt"] = "force"
    authorize_params["login_hint"] = "register"

    try:
        _preflight_authorization_request(authorize_params)
    except OAuth2Error as error:
        return None, _authlib_oauth_error(error)

    return authorize_params, None


@oauth2_bp.route("/registration-requests", methods=["POST"])
@nocache
def create_oauth_registration_request():
    """Create a short-lived browser redirect for client-initiated user registration."""
    data = request.form
    client, error = _authenticate_registration_request_client()
    if error is not None:
        return error

    authorize_params, error = _validate_registration_request(data, client)
    if error is not None:
        return error

    hints, error = _registration_request_hints(data)
    if error is not None:
        return error

    registration_request = dict(authorize_params)
    registration_request["client_name"] = client.name
    registration_request.update(hints)

    request_id, expires_in = create_registration_request(registration_request)
    redirect_to = url_for(".begin_registration_request", request_id=request_id, _external=True)
    response = jsonify({
        "request_id": request_id,
        "redirect_to": redirect_to,
        "expires_in": expires_in,
    })
    response.status_code = 201
    response.headers["Location"] = redirect_to
    return response


@oauth2_bp.route("/registration-requests/<request_id>", methods=["GET"])
@nocache
def begin_registration_request(request_id):
    registration_request = get_registration_request(request_id)
    if registration_request is None:
        return render_template("oauth/error.html", props=json.dumps({
            "error": {
                "name": "invalid_request",
                "description": "Registration request is invalid or expired.",
            }
        })), 400

    next_url = url_for(".begin_registration_request", request_id=request_id)
    if current_user.is_anonymous:
        return redirect(url_for("users.signup", next=next_url, registration_request=request_id))

    authorize_params = {
        key: registration_request[key]
        for key in REGISTRATION_REQUEST_STORED_AUTHORIZE_KEYS
        if key in registration_request
    }
    authorize_url = build_url(url_for(".authorize", _external=False), authorize_params)
    delete_registration_request(request_id)
    return redirect(authorize_url)


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
    cancel_url = build_url(grant.request.payload.data.get("redirect_uri"), {"error": "access_denied"})
    return render_template("oauth/prompt.html", props=json.dumps({
        "client_name": grant.client.name,
        "scopes": [{
            "name": scope.name,
            "description": scope.description
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
    cancel_url = build_url(redirect_uri, {"error": "access_denied"})
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

    return {
        "sub": str(user.id),
        "username": user.name,
        "member_since": user.member_since.isoformat() if user.member_since else None,
    }


@oauth2_bp.route("/introspect", methods=["POST"])
def introspect_token():
    return authorization_server.create_endpoint_response("introspection")


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
    scopes = [
        s[0] for s in db.session.query(OAuth2Scope.name).all()
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
    }
