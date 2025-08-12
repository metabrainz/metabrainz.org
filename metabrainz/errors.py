from flask import render_template, jsonify


def init_error_handlers(app):

    @app.errorhandler(400)
    def bad_request(error):
        return render_template('errors/400.html', error=error), 400

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html', error=error), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html', error=error), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template('errors/500.html', error=error), 500

    @app.errorhandler(503)
    def service_unavailable(error):
        return render_template('errors/503.html', error=error), 503
    
    @app.errorhandler(APIError)
    def api_error(error):
        return jsonify(error.to_dict()), error.status_code



class APIError(Exception):
    def __init__(self, message, status_code, payload=None):
        super(APIError, self).__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['code'] = self.status_code
        rv['error'] = self.message
        return rv

    def __str__(self):
        return self.message


class APINoContent(APIError):
    def __init__(self, message, payload=None):
        super(APINoContent, self).__init__(message, 204, payload)


class APINotFound(APIError):
    def __init__(self, message, payload=None):
        super(APINotFound, self).__init__(message, 404, payload)


class APIUnauthorized(APIError):
    def __init__(self, message, payload=None):
        super(APIUnauthorized, self).__init__(message, 401, payload)


class APIBadRequest(APIError):
    def __init__(self, message, payload=None):
        super(APIBadRequest, self).__init__(message, 400, payload)


class APIInternalServerError(APIError):
    def __init__(self, message, payload=None):
        super(APIInternalServerError, self).__init__(message, 500, payload)


class APIServiceUnavailable(APIError):
    def __init__(self, message, payload=None):
        super(APIServiceUnavailable, self).__init__(message, 503, payload)


class APIForbidden(APIError):
    def __init__(self, message, payload=None):
        super(APIForbidden, self).__init__(message, 403, payload)


