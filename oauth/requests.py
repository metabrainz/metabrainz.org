from functools import cached_property

from authlib.integrations.flask_oauth2.requests import FlaskOAuth2Request
from flask import session

AUTHORIZE_REDIRECT_SESSION_KEY = "authorize_redirect_session_key"


class CustomFlaskOAuth2Request(FlaskOAuth2Request):

    @cached_property
    def data(self):
        saved = session.get(AUTHORIZE_REDIRECT_SESSION_KEY, None)
        if saved:
            return saved
        return super().data
