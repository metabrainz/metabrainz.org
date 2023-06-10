from flask import redirect, url_for
from flask_login import LoginManager, current_user
from metabrainz.model.supporter import Supporter
from functools import wraps

login_manager = LoginManager()
login_manager.login_view = 'users.login'


@login_manager.user_loader
def load_supporter(supporter_id):
    return Supporter.get(id=supporter_id)


def login_forbidden(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.is_anonymous is False:
            return redirect(url_for('supporters.profile'))
        return f(*args, **kwargs)

    return decorated
