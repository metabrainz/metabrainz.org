from authlib.oauth2 import OAuth2Error
from flask import Blueprint, request, render_template, redirect
from flask_login import login_required, current_user

from metabrainz.decorators import nocache, crossdomain
from metabrainz.new_oauth.forms import ApplicationForm
from metabrainz.new_oauth.models.client import OAuth2Client
from metabrainz.new_oauth.provider import authorization_server
from metabrainz.new_oauth.models import db
from metabrainz.utils import build_url
from werkzeug.security import gen_salt

new_oauth_bp = Blueprint('new_oauth', __name__)


@new_oauth_bp.route('/create_client', methods=('GET', 'POST'))
@login_required
def create_client():
    form = ApplicationForm()
    if form.validate_on_submit():
        client_id = gen_salt(24)
        client = OAuth2Client(
            client_id=client_id,
            owner_id=current_user.id,
        )
        client_metadata = {
            "client_name": form.client_name,
            "client_uri": form["client_uri"],
            "grant_types": split_by_crlf(form["grant_type"]),
            "redirect_uris": split_by_crlf(form["redirect_uri"]),
            "response_types": split_by_crlf(form["response_type"]),
            "scope": form["scope"],
            "token_endpoint_auth_method": form["token_endpoint_auth_method"]
        }
        client.set_client_metadata(client_metadata)

        if form['token_endpoint_auth_method'] == 'none':
            client.client_secret = ''
        else:
            client.client_secret = gen_salt(48)

        db.session.add(client)
        db.session.commit()
    else:
        return render_template('oauth/create_client.html', form=form)

    return redirect('/')


@new_oauth_bp.route('/authorize', methods=['GET', 'POST'])
@login_required
def authorize_prompt():
    """ OAuth 2.0 authorization endpoint. """
    redirect_uri = request.args.get('redirect_uri')
    if request.method == 'GET':  # Client requests access
        try:
            grant = authorization_server.validate_consent_request(end_user=current_user)
        except OAuth2Error as error:
            return error.error  # FIXME: Add oauth error page
        return render_template('oauth/prompt.html', client=grant.client, scope=grant.request.scope,
                               cancel_url=build_url(redirect_uri, dict(error='access_denied')),
                               hide_navbar_links=True, hide_footer=True)
    if request.method == 'POST':  # User grants access to the client
        return authorization_server.create_authorization_response(grant_user=current_user)


@new_oauth_bp.route('/token', methods=['POST'])
@nocache
@crossdomain()
def oauth_token_handler():
    return authorization_server.create_token_response()


@new_oauth_bp.route('/revoke', methods=['POST'])
def revoke_token():
    return authorization_server.create_endpoint_response('revocation')


def split_by_crlf(s):
    return [v for v in s.splitlines() if v]
