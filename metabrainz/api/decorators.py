from functools import wraps
from flask import request
from werkzeug.exceptions import BadRequest, Forbidden
from metabrainz.model.token import Token


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
