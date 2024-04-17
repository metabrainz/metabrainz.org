from functools import wraps
from urllib.parse import quote_plus, urlparse

import requests
from flask import Request, current_app, has_request_context, g, request, redirect
from flask_login import UserMixin
from werkzeug.local import LocalProxy

from oauth.model import db
from oauth.model.editor import Editor

current_user = LocalProxy(lambda: _get_user())


class User(UserMixin):

    def __init__(self, user_id, user_name):
        self.id = user_id
        self.user_id = user_id
        self.user_name = user_name

    def is_anonymous(self):
        return self.id is not None

    def is_active(self):
        return self.id is not None

    def __str__(self):
        return f"User(user_id={self.id}, user_name={self.user_name})"


ANONYMOUS_USER = User(None, None)


def _get_user():
    if has_request_context():
        if "_login_user" not in g:
            g._login_user = load_user_from_request(request)
        return g._login_user
    return ANONYMOUS_USER


def login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated():
            return redirect(f"{current_app.config['MUSICBRAINZ_SERVER']}/login?returnto=" + quote_plus(request.url))
        return func(*args, **kwargs)

    return decorated_view


def load_user_from_request(_request: Request):
    if "musicbrainz_server_session" in _request.cookies:
        response = requests.get(
            f"{current_app.config['MUSICBRAINZ_SERVER']}/ws/js/check-login",
            cookies=_request.cookies
        )
        if response.status_code == 200:
            data = response.json()
            if data["id"] is not None:
                return User(user_id=data["id"], user_name=data["name"])

    return ANONYMOUS_USER


def load_user_from_db(user_id: int):
    user = db.session.query(Editor).filter_by(id=user_id, deleted=False).first()
    if user is None:
        return ANONYMOUS_USER
    else:
        return User(user_id=user.id, user_name=user.name)
