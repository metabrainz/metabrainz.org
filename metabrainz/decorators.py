from functools import wraps, update_wrapper
from datetime import timedelta
from flask import request, current_app, make_response
import six
import requests
from metabrainz.errors import APIBadRequest, APIUnauthorized, APIForbidden

NOTIFICATION_SCOPE = 'notification'


def add_response_headers(headers=None):
    """This decorator adds the headers passed in to the response."""
    if headers is None:
        headers = {}

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            resp = make_response(f(*args, **kwargs))
            h = resp.headers
            for header, value in headers.items():
                h[header] = value
            return resp
        return decorated_function

    return decorator


def nocache(f):
    @wraps(f)
    @add_response_headers({'Cache-Control': 'no-store'})
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function


def crossdomain(origin='*', methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    # Based on snippet by Armin Ronacher located at http://flask.pocoo.org/snippets/56/.
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, six.string_types):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, six.string_types):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator


def ccg_token_required(f):
    @wraps(f)
    def decorated(*args,**kwargs):
        token = request.args.get('token')
        if not token:
            raise APIBadRequest('Missing access token.')
        data = {
            "client_id": current_app.config["MUSICBRAINZ_CLIENT_ID"],
            "client_secret": current_app.config["MUSICBRAINZ_CLIENT_SECRET"],
            "token": token
        }
        response = requests.post(current_app.config["OAUTH_INTROSPECTION_URL"], data).json()
        if not response.get("active"):
            raise APIUnauthorized('Invalid or Expired access token.')
        if NOTIFICATION_SCOPE not in response["scope"]:
            raise APIForbidden('Missing notification scope.')
        if response["client_id"] not in current_app.config["OAUTH2_WHITELISTED_CCG_CLIENTS"]:
            raise APIForbidden('Client is not an official MeB project.')

        return f(*args, **kwargs)
    
    return decorated
