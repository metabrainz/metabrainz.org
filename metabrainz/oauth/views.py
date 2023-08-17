from authlib.oauth2 import OAuth2Error
from flask import Blueprint, request, render_template, redirect, url_for, jsonify
from flask_login import login_required, current_user
from werkzeug.security import gen_salt

from metabrainz.decorators import nocache, crossdomain
from metabrainz.model import db
from metabrainz.model.oauth.client import OAuth2Client
from metabrainz.model.oauth.token import OAuth2Token
from metabrainz.model.user import User
from metabrainz.oauth.forms import ApplicationForm
from metabrainz.oauth.provider import authorization_server
from metabrainz.utils import build_url

oauth_bp = Blueprint('new_oauth', __name__)


@oauth_bp.route('/create_client', methods=('GET', 'POST'))
@login_required
def create_client():
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
        return render_template('oauth/create_client.html', form=form)

    return redirect(url_for("index.home"))


@oauth_bp.route('/authorize', methods=['GET', 'POST'])
@login_required
def authorize_prompt():
    """ OAuth 2.0 authorization endpoint. """
    redirect_uri = request.args.get('redirect_uri')
    if request.method == 'GET':  # Client requests access
        try:
            grant = authorization_server.get_consent_grant(end_user=current_user)
        except OAuth2Error as error:
            return jsonify({
                "error": error.error,
                "description": error.description
            })  # FIXME: Add oauth error page
        return render_template('oauth/prompt.html', client=grant.client, scope=grant.request.scope,
                               cancel_url=build_url(redirect_uri, {"error": "access_denied"}),
                               hide_navbar_links=True, hide_footer=True)
    else:
        # TODO: Validate that user grants access to the client
        return authorization_server.create_authorization_response(grant_user=current_user)


@oauth_bp.route('/token', methods=['POST'])
@nocache
@crossdomain()
def oauth_token_handler():
    return authorization_server.create_token_response()


@oauth_bp.route('/revoke', methods=['POST'])
def revoke_token():
    return authorization_server.create_endpoint_response("revocation")


@oauth_bp.route('/userinfo', methods=['GET'])
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
