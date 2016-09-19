from flask import request
from datetime import datetime, timedelta
from functools import wraps
from metabrainz.utils import generate_string
from metabrainz.db.oauth import client as db_client, grant as db_grant, token as db_token, AVAILABLE_SCOPES
from metabrainz.oauth import exceptions
import pytz
import six


class MetaBrainzAuthorizationProvider(object):

    token_length = 40
    grant_expire = 60
    token_expire = 3600

    @staticmethod
    def validate_authorization_header(value):
        if not value or isinstance(value, six.string_types) is False:
            return False

        authorization = value.split()
        if len(authorization) != 2:
            return False

        if authorization[0] != 'Bearer':
            return False

        return True

    @staticmethod
    def validate_client_id(client_id):
        if not client_id:
            return False
        return db_client.get(client_id) is not None

    @staticmethod
    def validate_client_secret(client_id, client_secret):
        client = db_client.get(client_id)
        if client is None:
            return False
        else:
            return client["client_secret"] == client_secret

    @staticmethod
    def validate_client_redirect_uri(client_id, redirect_uri):
        client = db_client.get(client_id)
        if client is None or isinstance(redirect_uri, six.string_types) is False:
            return False
        else:
            return client["redirect_uri"] == redirect_uri.split('?')[0]

    def validate_grant_redirect_uri(self, client_id, code, redirect_uri):
        grant = self.fetch_grant(client_id, code)
        if grant is None:
            return False
        else:
            return grant["redirect_uri"] == redirect_uri

    def validate_grant_scope(self, client_id, code, scope):
        grant = self.fetch_grant(client_id, code)
        return self.validate_scope(scope, grant["scopes"])

    def validate_grant(self, client_id, code):
        grant = self.fetch_grant(client_id, code)
        if grant is None:
            return False
        return (datetime.now(pytz.utc) > grant["expires"]) is False

    def validate_token_scope(self, client_id, refresh_token, scope):
        token = self.fetch_token(client_id, refresh_token)
        return self.validate_scope(scope, token["scopes"])

    def validate_token(self, client_id, refresh_token):
        return self.fetch_token(client_id, refresh_token) is not None

    @staticmethod
    def validate_scope(scopes, valid_scopes=AVAILABLE_SCOPES):
        """Validate a string with comma-separated scopes.

        Args:
            scopes (str): String with scopes. For example, 'account,email,notes'.
            valid_scopes (list): Optional list of available scopes.
        """
        if not scopes or isinstance(scopes, six.string_types) is False:
            return False
        scopes = scopes.split()
        for scope in scopes:
            if scope not in valid_scopes:
                return False
        return True

    @staticmethod
    def persist_grant(client_id, code, scopes, expires, redirect_uri, user_id):
        return db_grant.create(
            client_id=client_id,
            code=code,
            scopes=scopes,
            expires=expires,
            redirect_uri=redirect_uri,
            user_id=user_id,
        )

    @staticmethod
    def persist_token(client_id, scope, refresh_token, access_token, expires, user_id):
        return db_token.create(
            client_id=client_id,
            scopes=scope,
            access_token=access_token,
            refresh_token=refresh_token,
            expires=expires,
            user_id=user_id,
        )

    @staticmethod
    def fetch_grant(client_id, code):
        return db_grant.get(client_id=client_id, code=code)

    @staticmethod
    def fetch_token(client_id, refresh_token):
        return db_token.get_by_client_id_and_refresh_token(
            client_id=client_id, refresh_token=refresh_token)

    @staticmethod
    def fetch_access_token(access_token):
        return db_token.get_by_token(access_token)

    @staticmethod
    def discard_grant(client_id, code):
        db_grant.delete_by_code(client_id=client_id, code=code)

    @staticmethod
    def discard_token(client_id, refresh_token):
        db_token.delete_by_refresh_token(client_id=client_id, refresh_token=refresh_token)

    @staticmethod
    def discard_client_user_tokens(client_id, user_id):
        db_token.delete_by_user_id(client_id=client_id, user_id=user_id)

    def validate_authorization_request(self, client_id, response_type, redirect_uri, scope=None):
        if self.validate_client_id(client_id) is False:
            raise exceptions.InvalidClient
        if response_type != 'code':
            raise exceptions.UnsupportedResponseType
        if self.validate_client_redirect_uri(client_id, redirect_uri) is False:
            raise exceptions.InvalidRedirectURI
        if scope and not self.validate_scope(scope):
            raise exceptions.InvalidScope

    def validate_token_request(self, grant_type, client_id, client_secret, redirect_uri, code, refresh_token):
        if self.validate_client_id(client_id) is False:
            raise exceptions.InvalidClient
        if self.validate_client_secret(client_id, client_secret) is False:
            raise exceptions.InvalidClient
        if grant_type == 'authorization_code':
            if self.validate_grant(client_id, code) is False:
                raise exceptions.InvalidGrant
            if self.validate_grant_redirect_uri(client_id, code, redirect_uri) is False:
                raise exceptions.InvalidRedirectURI
        elif grant_type == 'refresh_token':
            if self.validate_token(client_id, refresh_token) is False:
                raise exceptions.InvalidGrant
        else:
            raise exceptions.UnsupportedGrantType

    def generate_grant(self, client_id, user_id, redirect_uri, scope=None):
        code = generate_string(self.token_length)
        expires = datetime.now(pytz.utc) + timedelta(seconds=self.grant_expire)
        self.persist_grant(client_id, code, scope, expires, redirect_uri, user_id)
        return code

    def generate_token(self, client_id, refresh_token, user_id, scope=None):
        if not refresh_token:
            refresh_token = generate_string(self.token_length)
        access_token = generate_string(self.token_length)
        expires = datetime.now(pytz.utc) + timedelta(seconds=self.token_expire)
        self.persist_token(client_id, scope, refresh_token, access_token, expires, user_id)
        return access_token, 'Bearer', self.token_expire, refresh_token

    def get_authorized_user(self, scopes):
        authorization = request.headers.get('Authorization')
        if self.validate_authorization_header(authorization) is False:
            raise exceptions.NotAuthorized

        access_token = authorization.split()[1]
        token = self.fetch_access_token(access_token)
        if token is None:
            raise exceptions.InvalidToken

        if token["expires"] < datetime.now(pytz.utc):
            raise exceptions.InvalidToken

        for scope in scopes:
            if scope not in token["scopes"]:
                raise exceptions.InvalidToken

        return token["user_id"]

    def require_auth(self, *scopes):
        def decorator(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                user_id = self.get_authorized_user(scopes)
                kwargs.update(dict(user_id=user_id))
                return f(*args, **kwargs)
            return decorated
        return decorator
