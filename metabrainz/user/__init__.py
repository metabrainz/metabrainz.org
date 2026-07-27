from functools import wraps

from flask import abort, flash, redirect, request, url_for
from flask_login import LoginManager, current_user
from flask_login.utils import login_url

from metabrainz.model.user import User

login_manager = LoginManager()
login_manager.login_view = "users.login"
login_manager.refresh_view = "users.reauthenticate"
login_manager.needs_refresh_message = "Please re-enter your password to continue."
login_manager.needs_refresh_message_category = "info"


@login_manager.user_loader
def load_user(login_id):
    try:
        return User.get(login_id=login_id)
    except (ValueError, TypeError):
        return None


@login_manager.unauthorized_handler
def unauthorized():
    login_view = (
        "users.signup"
        if request.args.get("login_hint") == "register"
        else login_manager.login_view
    )
    if not login_view:
        abort(401)

    if login_manager.login_message:
        flash(
            login_manager.login_message,
            category=login_manager.login_message_category,
        )

    return redirect(login_url(login_view, next_url=request.url))


def login_forbidden(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.is_anonymous is False:
            return redirect(url_for("index.home"))
        return f(*args, **kwargs)

    return decorated
