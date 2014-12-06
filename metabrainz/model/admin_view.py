from flask_admin.contrib.sqla import ModelView
from flask import request, Response, current_app
from werkzeug.exceptions import Unauthorized


def _check_admin_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == current_app.config['ADMIN_USERNAME'] and password == current_app.config['ADMIN_PASSWORD']


class AdminView(ModelView):
    """All admin views that shouldn't be available to public, must be based on this class."""

    def is_accessible(self):
        auth = request.authorization
        if not auth or not _check_admin_auth(auth.username, auth.password):
            raise Unauthorized(response=Response(
                'Could not verify your access level for that URL.\n'
                'You have to login with proper credentials.', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'}))
        return True
