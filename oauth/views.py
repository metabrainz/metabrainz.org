import json
from datetime import timedelta

from authlib.oauth2.rfc6749 import InvalidRequestError
from flask import Blueprint, request, render_template, redirect, url_for, jsonify, make_response
from flask_babel import gettext
from flask_wtf.csrf import generate_csrf
from werkzeug.exceptions import NotFound, Forbidden
from werkzeug.security import gen_salt

from metabrainz import flash
from metabrainz.decorators import nocache, crossdomain
from oauth import login
from oauth.login import login_required, current_user
from oauth.model import db, OAuth2RefreshToken
from oauth.model.client import OAuth2Client
from oauth.model.scope import get_scopes
from oauth.model.access_token import OAuth2AccessToken
from oauth.forms import ApplicationForm, AuthorizationForm
from oauth.provider import authorization_server
from metabrainz.utils import build_url

oauth2_bp = Blueprint("oauth2", __name__)


@oauth2_bp.route("/client/list")
@login_required
def index():
    applications = db\
        .session\
        .query(OAuth2Client)\
        .filter(OAuth2Client.owner_id == current_user.id)\
        .order_by(OAuth2Client.client_id_issued_at)\
        .all()
    tokens = db\
        .session\
        .query(OAuth2AccessToken)\
        .filter(
            OAuth2AccessToken.user_id == current_user.id,
            OAuth2AccessToken.revoked.is_(False)
        )\
        .order_by(OAuth2AccessToken.issued_at.desc())\
        .all()
    tokens = {t for t in tokens if not t.is_expired()}
    return render_template("oauth/index.html", props=json.dumps({
        "applications": [{
            "name": application.name,
            "description": application.description,
            "client_id": application.client_id,
            "client_secret": application.client_secret,
            "website": application.website,
            "redirect_uris": application.redirect_uris,
        } for application in applications],
        "tokens": [{
            "name": token.client.name,
            "scopes": [{
                "name": scope.name,
                "description": scope.description
            } for scope in token.scopes],
            "client_id": token.client.client_id,
            "website": token.client.website,
        } for token in tokens],
    }))


@oauth2_bp.route("/client/create", methods=("GET", "POST"))
@login_required
def create():
    form = ApplicationForm()
    if form.validate_on_submit():
        client_id = gen_salt(24)
        client_secret = gen_salt(48)
        client = OAuth2Client(
            client_id=client_id,
            client_secret=client_secret,
            owner_id=current_user.id,
            name=form.client_name.data,
            description=form.description.data,
            website=form.website.data,
            redirect_uris=form.redirect_uris.data
        )
        db.session.add(client)
        db.session.commit()
        return redirect(url_for(".index"))

    form_errors = {
        "client_name": " ".join(form.client_name.errors),
        "website": " ".join(form.website.errors),
        "description": " ".join(form.description.errors),
        "redirect_uris": [" ". join(errors) for errors in form.redirect_uris.errors],
        "csrf_token": " ".join(form.csrf_token.errors),
    }
    form_data = dict(**form.data)
    form_data.pop("csrf_token", None)

    return render_template("oauth/create.html", props=json.dumps({
        "csrf_token": generate_csrf(),
        "is_edit_mode": False,
        "initial_form_data": form_data,
        "initial_errors": form_errors
    }))


@oauth2_bp.route("/client/edit/<client_id>", methods=["GET", "POST"])
@login_required
def edit(client_id):
    application = db.session().query(OAuth2Client).filter(OAuth2Client.client_id == client_id).first()
    if application is None:
        raise NotFound()
    if application.owner_id != current_user.id:
        raise Forbidden()

    form = ApplicationForm()
    if form.validate_on_submit():
        application.name = form.client_name.data
        application.description = form.description.data
        application.website = form.website.data
        application.redirect_uris = form.redirect_uris.data
        db.session.commit()
        flash.success(gettext("You have updated an application!"))
        return redirect(url_for(".index"))

    form_errors = {
        "client_name": " ".join(form.client_name.errors),
        "website": " ".join(form.website.errors),
        "description": " ".join(form.description.errors),
        "redirect_uris": [" ". join(errors) for errors in form.redirect_uris.errors]
    }
    form_data = {
        "client_name": form.client_name.data or application.name,
        "description": form.description.data or application.description,
        "website": form.website.data or application.website,
    }

    if form.redirect_uris.data and len(form.redirect_uris.data) > 0 and form.redirect_uris.data[0]:
        form_data["redirect_uris"] = form.redirect_uris.data
    else:
        form_data["redirect_uris"] = application.redirect_uris

    return render_template("oauth/edit.html", props=json.dumps({
        "client_name": form_data["client_name"],
        "is_edit_mode": True,
        "csrf_token": generate_csrf(),
        "initial_form_data": form_data,
        "initial_errors": form_errors
    }))


@oauth2_bp.route("/client/delete/<client_id>", methods=["POST"])
@login_required
def delete(client_id):
    application = db.session().query(OAuth2Client).filter(OAuth2Client.client_id == client_id).first()
    if application is None:
        raise NotFound()
    if application.owner_id != current_user.id:
        raise Forbidden()

    db.session.delete(application)
    db.session.commit()
    flash.success(gettext("You have deleted an application."))
    return redirect(url_for(".index"))


@oauth2_bp.route("/authorize", methods=["GET", "POST"])
@login_required
def authorize():
    """ OAuth 2.0 authorization endpoint. """
    form = AuthorizationForm()
    redirect_uri = request.args.get("redirect_uri")
    if not redirect_uri:
        raise InvalidRequestError(description="Missing \"redirect_uri\" in request.")
    cancel_url = build_url(redirect_uri, {"error": "access_denied"})

    approval = request.args.get("approval_prompt", "auto")
    if approval not in {"auto", "force"}:
        raise InvalidRequestError(description="Invalid \"approval_prompt\" in request.")

    if request.method == "GET":
        grant = authorization_server.get_consent_grant(end_user=current_user)
        scopes = get_scopes(db.session, grant.request.scope)

        # TODO: decide if auto approval should revoke existing tokens issued to the same client for the given userr
        #   if not improve UI for approved applications in the user page.
        if approval == "auto" and grant.client.check_already_approved(current_user.id, scopes):
            return authorization_server.create_authorization_response(grant_user=current_user)

        return render_template("oauth/prompt.html", props=json.dumps({
            "client_name": grant.client.name,
            "scopes": [{
                "name": scope.name,
                "description": scope.description
            } for scope in scopes],
            "cancel_url": cancel_url,
            "csrf_token": generate_csrf(),
        }))
    else:
        if form.validate_on_submit():
            return authorization_server.create_authorization_response(grant_user=current_user)
        else:
            return redirect(cancel_url)


@oauth2_bp.route("/client/<client_id>/revoke/user", methods=["POST"])
@login_required
def revoke_client_for_user(client_id):
    application = db.session().query(OAuth2Client).filter(OAuth2Client.client_id == client_id).first()

    access_tokens = db.session.query(OAuth2AccessToken).filter_by(
        client_id=application.id,
        user_id=current_user.id
    ).all()
    for token in access_tokens:
        token.revoked = True
    db.session.add_all(access_tokens)

    refresh_tokens = db.session.query(OAuth2RefreshToken).filter_by(
        client_id=application.id,
        user_id=current_user.id
    ).all()
    for token in refresh_tokens:
        token.revoked = True
    db.session.add_all(refresh_tokens)

    flash.success("Revoked tokens successfully!")
    return redirect(url_for(".index"))


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
    # TODO: Discuss merging with introspection endpoint
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "missing auth header"}), 401
    try:
        token = auth_header.split(" ")[1]
    except (ValueError, KeyError):
        return jsonify({"error": "invalid auth header"}), 401

    token = db.session\
        .query(OAuth2AccessToken)\
        .filter_by(access_token=token)\
        .one_or_none()

    if token is None:
        return jsonify({"error": "invalid access token"}), 403

    if token.is_expired():
        return jsonify({"error": "expired access token"}), 403

    user = login.load_user_from_db(token.user_id)

    return {
        "sub": user.user_name,
        "metabrainz_user_id": user.id
    }


@oauth2_bp.route("/introspect", methods=["POST"])
def introspect_token():
    return authorization_server.create_endpoint_response("introspection")


def split_by_crlf(s):
    return [v for v in s.splitlines() if v]
