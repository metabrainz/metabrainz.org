from flask import Blueprint, render_template, redirect, request, jsonify
from flask_login import login_required, current_user
from metabrainz.db.oauth import client as db_client
from metabrainz.oauth import oauth_provider
from metabrainz.oauth import exceptions
from metabrainz.utils import build_url
from metabrainz.decorators import nocache, crossdomain

oauth_bp = Blueprint('oauth', __name__)


@oauth_bp.route('/authorize', methods=['GET', 'POST'])
@login_required
def authorize_prompt():
    """OAuth 2.0 authorization endpoint."""
    response_type = request.args.get('response_type')
    client_id = request.args.get('client_id')
    redirect_uri = request.args.get('redirect_uri')
    scope = request.args.get('scope')
    state = request.args.get('state')

    if request.method == 'GET':  # Client requests access
        oauth_provider.validate_authorization_request(client_id, response_type, redirect_uri, scope)
        client = db_client.get(client_id)
        return render_template('oauth/prompt.html', client=client, scope=scope,
                               cancel_url=build_url(redirect_uri, dict(error='access_denied')),
                               hide_navbar_links=True, hide_footer=True)

    if request.method == 'POST':  # User grants access to the client
        oauth_provider.validate_authorization_request(client_id, response_type, redirect_uri, scope)
        code = oauth_provider.generate_grant(client_id, current_user.id, redirect_uri, scope)
        return redirect(build_url(redirect_uri, dict(code=code, state=state)))


@oauth_bp.route('/token', methods=['POST'])
@nocache
@crossdomain()
def oauth_token_handler():
    """OAuth 2.0 token endpoint.

    :form string client_id:
    :form string client_secret:
    :form string redirect_uri:
    :form string grant_type: ``authorization_code`` or ``refresh_token``
    :form string code: (not required if grant_type is ``refresh_token``)
    :form string refresh_token: (not required if grant_type is ``authorization_code``)

    :resheader Content-Type: *application/json*
    """
    client_id = request.form.get('client_id')
    client_secret = request.form.get('client_secret')
    redirect_uri = request.form.get('redirect_uri')
    grant_type = request.form.get('grant_type')
    code = request.form.get('code')
    refresh_token = request.form.get('refresh_token')

    oauth_provider.validate_token_request(grant_type, client_id, client_secret, redirect_uri, code, refresh_token)

    if grant_type == 'authorization_code':
        grant = oauth_provider.fetch_grant(client_id, code)
        user_id = grant.user.id
        scope = grant.scopes
    elif grant_type == 'refresh_token':
        token = oauth_provider.fetch_token(client_id, refresh_token)
        user_id = token["user_id"]
        scope = token["scopes"]
    else:
        raise exceptions.UnsupportedGrantType(
            "Specified grant_type is unsupported. "
            "Please, use authorization_code or refresh_token."
        )

    # Deleting grant and/or existing token(s)
    # TODO(roman): Check if that's necessary:
    oauth_provider.discard_grant(client_id, code)
    oauth_provider.discard_client_user_tokens(client_id, user_id)

    access_token, token_type, expires_in, refresh_token = \
        oauth_provider.generate_token(client_id, refresh_token, user_id, scope)

    return jsonify(dict(
        access_token=access_token,
        token_type=token_type,
        expires_in=expires_in,
        refresh_token=refresh_token,
    ))
