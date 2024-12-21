from flask import redirect, url_for
from flask_login import LoginManager, current_user
from functools import wraps

from metabrainz.model.user import User

login_manager = LoginManager()
login_manager.login_view = "users.login"


@login_manager.user_loader
def load_user(user_id):
    return User.get(id=user_id)


def login_forbidden(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.is_anonymous is False:
            return redirect(url_for("index.home"))
        return f(*args, **kwargs)

    return decorated
