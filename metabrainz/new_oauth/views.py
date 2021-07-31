from authlib.oauth2 import OAuth2Error
from flask import Blueprint, request, render_template
from flask_login import login_required, current_user

from metabrainz.decorators import nocache, crossdomain
from metabrainz.new_oauth.provider import authorization_server
from metabrainz.utils import build_url

new_oauth_bp = Blueprint('new_oauth', __name__)


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
