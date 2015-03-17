from functools import wraps
from flask import request
from werkzeug.exceptions import BadRequest, Forbidden
from metabrainz.model.token import Token
from metabrainz.model.access_log import AccessLog


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        access_token = request.args.get('token')
        if not access_token:
            raise BadRequest("You need to provide an access token.")
        if not Token.is_valid(access_token):
            raise Forbidden("Provided access token is invalid.")
        return f(*args, **kwargs)

    return decorated


def tracked(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        response = f(*args, **kwargs)
        if response.status_code == 200:
            AccessLog.create_record(request.args.get('token'))
        return response

    return decorated
