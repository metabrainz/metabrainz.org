from flask import render_template, jsonify
from metabrainz.oauth.exceptions import OAuthError


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

    @app.errorhandler(OAuthError)
    def oauth_error_handler(error):
        return jsonify(error=error.code, description=error.desc), error.status
