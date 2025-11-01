import json

from authlib.oauth2.rfc6749 import InvalidRequestError
from flask import Blueprint, request, render_template, redirect, url_for, jsonify, flash, g, current_app
from flask_babel import gettext
from flask_login import login_required, current_user
from flask_wtf.csrf import generate_csrf
from werkzeug.exceptions import NotFound, Forbidden
from urllib.parse import urljoin

from metabrainz.model.user import User
from metabrainz.decorators import nocache, crossdomain
from metabrainz.oauth.generator import create_client_secret, create_client_id
from metabrainz.model import db, OAuth2RefreshToken, OAuth2Scope, OAuth2Client, get_scopes, OAuth2AccessToken
from metabrainz.oauth.forms import ApplicationForm, AuthorizationForm, DeleteApplicationForm
from metabrainz.oauth.authorization_server import authorization_server
from metabrainz.utils import build_url

oauth2_bp = Blueprint("oauth2", __name__)
wellknown_bp = Blueprint("well-known", __name__)


@oauth2_bp.after_request
def after_oauth2_request(response):
    """ Add security headers for Referrer-Policy, Content-Security-Policy, Cache-Control and X-Frame-Options """
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    # todo: add content-security-policy headers
    return response


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
        "sub": user.name,
        "metabrainz_user_id": user.id
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
    url_prefix = urljoin(current_app.config["MUSICBRAINZ_SERVER"], current_app.config["OAUTH2_BLUEPRINT_PREFIX"])
    return {
        "issuer": "https://metabrainz.org",
        "authorization_endpoint": f"{url_prefix}/authorize",
        "token_endpoint": f"{url_prefix}/token",
        "userinfo_endpoint": f"{url_prefix}/userinfo",
        "jwks_uri": f"{url_prefix}/.well-known/jwks.json",
        "scopes_supported": scopes,
        "response_types_supported": ["code", "id_token token", "id_token"],
        "response_modes_supported": ["query", "fragment"],
        "grant_types_supported": ["authorization_code", "refresh_token", "implicit"],
        "id_token_signing_alg_values_supported": ["ES256", "none"],
        "subject_types_supported": ["public"],
    }
