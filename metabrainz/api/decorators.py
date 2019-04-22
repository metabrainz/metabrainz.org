from functools import wraps
from flask import request, current_app
from werkzeug.wrappers import Response
from metabrainz.model.token import Token
from metabrainz.model.access_log import AccessLog


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        access_token = request.args.get('token')
        if not access_token:
            return Response("You need to provide an access token!\n", status=400)
        if not Token.is_valid(access_token):
            return Response("Provided access token is invalid!\n", status=403)
        return f(*args, **kwargs)

    return decorated


def tracked(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        response = f(*args, **kwargs)
        if response.status_code in (200, 307):
            ip_addr = request.environ.get('REMOTE_ADDR', None)
            if not ip_addr:
                ip_addr = request.remote_addr
            AccessLog.create_record(request.args.get('token'), ip_addr)
        return response

    return decorated
