from flask import redirect, url_for
from flask_login import LoginManager, current_user
from functools import wraps

from metabrainz.model.user import User

login_manager = LoginManager()
login_manager.login_view = "users.login"
login_manager.refresh_view = "users.login"
login_manager.needs_refresh_message = "Please re-enter your password to continue."
login_manager.needs_refresh_message_category = "info"


@login_manager.user_loader
def load_user(login_id):
    try:
        return User.get(login_id=login_id)
    except (ValueError, TypeError):
        return None

def login_forbidden(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.is_anonymous is False:
            return redirect(url_for("index.home"))
        return f(*args, **kwargs)

    return decorated
