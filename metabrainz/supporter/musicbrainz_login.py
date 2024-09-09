from rauth import OAuth2Service
from flask import request, url_for, current_app
from metabrainz import session
from metabrainz.utils import generate_string
import json

_musicbrainz_service = None


def init(base_url, client_id, client_secret):
    global _musicbrainz_service
    _musicbrainz_service = OAuth2Service(
        name='musicbrainz',
        base_url=base_url,
        authorize_url=base_url+"oauth2/authorize",
        access_token_url=base_url+"oauth2/token",
        client_id=client_id,
        client_secret=client_secret,
    )


def get_supporter(authorization_code):
    """Fetches info about current supporter.

    Returns:
        MusicBrainz username and email address.
    """
    s = _musicbrainz_service.get_auth_session(data={
        'code': authorization_code,
        'grant_type': 'authorization_code',
        'redirect_uri': url_for(
            'supporters.musicbrainz_post',
            _external=True,
            _scheme=current_app.config['PREFERRED_URL_SCHEME'],
        )
    }, decoder=lambda content: json.loads(content.decode("utf-8")))
    data = s.get('oauth2/userinfo').json()
    return data.get('sub'), data.get('email'), data.get("metabrainz_user_id")


def get_authentication_uri():
    """Prepare and return URL to authentication service login form."""
    csrf = generate_string(20)
    session.persist_data(csrf=csrf)
    params = {
        'response_type': 'code',
        'redirect_uri': url_for(
            'supporters.musicbrainz_post',
            _external=True,
            _scheme=current_app.config['PREFERRED_URL_SCHEME'],
        ),
        'scope': 'profile email',
        'state': csrf,
    }
    return _musicbrainz_service.get_authorize_url(**params)


def validate_post_login():
    """Function validating parameters passed after redirection from login form.
    Should return True, if everything is ok, or False, if something went wrong.
    """
    if request.args.get('error'):
        return False
    # TODO(roman): Maybe check if both are there:
    if session.fetch_data('csrf') != request.args.get('state'):
        return False
    return True
