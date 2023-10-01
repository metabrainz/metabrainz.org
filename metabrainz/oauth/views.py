from authlib.oauth2 import OAuth2Error
from flask import Blueprint, request, render_template, redirect, url_for, jsonify
from flask_babel import gettext
from flask_login import login_required, current_user
from werkzeug.exceptions import NotFound
from werkzeug.security import gen_salt

from metabrainz import flash
from metabrainz.decorators import nocache, crossdomain
from metabrainz.model import db
from metabrainz.model.oauth.client import OAuth2Client
from metabrainz.model.oauth.token import OAuth2Token
from metabrainz.model.user import User
from metabrainz.oauth.forms import ApplicationForm, AuthorizationForm
from metabrainz.oauth.provider import authorization_server
from metabrainz.utils import build_url

oauth_bp = Blueprint('oauth', __name__)


@oauth_bp.route('/list')
@login_required
def index():
    applications = db\
        .session\
        .query(OAuth2Client)\
        .filter(OAuth2Client.owner_id == current_user.id)\
        .all()
    tokens = db\
        .session\
        .query(OAuth2Token)\
        .filter(OAuth2Token.user_id == current_user.id)\
        .all()
    return render_template("oauth/index.html", applications=applications, tokens=tokens)


@oauth_bp.route('/create_client', methods=('GET', 'POST'))
@login_required
def create():
    form = ApplicationForm()
    if form.validate_on_submit():
        client_id = gen_salt(24)
        client = OAuth2Client(
            client_id=client_id,
            owner_id=current_user.id,
            name=form.client_name.data,
            description=form.description.data,
            website=form.website.data,
            redirect_uris=[form.redirect_uri.data]
        )
        # TODO: Fix use of these columns
        # client_metadata = {
        #     "grant_types": split_by_crlf(form["grant_type"]),
        #     "response_types": split_by_crlf(form["response_type"]),
        #     "token_endpoint_auth_method": form["token_endpoint_auth_method"]
        # }

        # if form["token_endpoint_auth_method"] == "none":
        #     client.client_secret = ""
        # else:
        #     client.client_secret = gen_salt(48)

        client.client_secret = gen_salt(48)
        db.session.add(client)
        db.session.commit()
    else:
        return render_template('oauth/create.html', form=form)

    return redirect(url_for(".index"))


@oauth_bp.route('/edit/<client_id>', methods=['GET', 'POST'])
@login_required
def edit(client_id):
    application = db.session().query(OAuth2Client).filter(OAuth2Client.client_id == client_id).first()
    if application is None or application.owner_id != current_user.id:
        raise NotFound()

    form = ApplicationForm()
    if form.validate_on_submit():
        application.name = form.client_name.data
        application.description = form.description.data
        application.website = form.website.data
        application.redirect_uris = [form.redirect_uri.data]
        db.session.commit()
        flash.success(gettext("You have updated an application!"))
        return redirect(url_for('.index'))

    form.client_name.data = application.name
    form.description.data = application.description
    form.website.data = application.website
    form.redirect_uri.data = application.redirect_uris[0]
    return render_template("oauth/edit.html", form=form)


@oauth_bp.route('/delete/<client_id>')
@login_required
def delete(client_id):
    application = db.session().query(OAuth2Client).filter(OAuth2Client.client_id == client_id).first()
    if application is None or application.owner_id != current_user.id:
        raise NotFound()

    db.session.delete(application)
    db.session.commit()
    flash.success(gettext('You have deleted an application.'))
    return redirect(url_for('.index'))


@oauth_bp.route('/authorize', methods=['GET', 'POST'])
@login_required
def authorize():
    """ OAuth 2.0 authorization endpoint. """
    form = AuthorizationForm()
    redirect_uri = request.args.get('redirect_uri')
    cancel_url = build_url(redirect_uri, {"error": "access_denied"})

    if request.method == 'GET':  # Client requests access
        try:
            grant = authorization_server.get_consent_grant(end_user=current_user)
        except OAuth2Error as error:
            return jsonify({
                "error": error.error,
                "description": error.description
            })  # FIXME: Add oauth error page
        return render_template('oauth/prompt.html', client=grant.client, scope=grant.request.scope,
                               cancel_url=cancel_url, hide_navbar_links=True, hide_footer=True, form=form)
    else:
        if form.validate_on_submit():
            return authorization_server.create_authorization_response(grant_user=current_user)
        else:
            return redirect(cancel_url)


@oauth_bp.route('/token', methods=['POST'])
@nocache
@crossdomain()
def oauth_token_handler():
    return authorization_server.create_token_response()


@oauth_bp.route('/revoke', methods=['POST'])
def revoke():
    return authorization_server.create_endpoint_response("revocation")


@oauth_bp.route('/userinfo', methods=['GET', 'POST'])
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
        .query(OAuth2Token)\
        .filter_by(access_token=token)\
        .one_or_none()

    if token is None:
        return jsonify({"error": "invalid access token"}), 403

    if token.is_expired():
        return jsonify({"error": "expired access token"}), 403

    user = db.session\
        .query(User)\
        .filter_by(id=token.user_id)\
        .first()

    return {
        "sub": user.name,
        "metabrainz_user_id": user.id
    }


@oauth_bp.route('/introspect', methods=['POST'])
def introspect_token():
    return authorization_server.create_endpoint_response("introspection")


def split_by_crlf(s):
    return [v for v in s.splitlines() if v]
