class OAuthError(Exception):
    def __init__(self, code=None, desc=None, status=400):
        self.code = code
        self.desc = desc
        self.status = status


class UnsupportedResponseType(OAuthError):
    def __init__(self):
        super(UnsupportedResponseType, self).__init__(
            code='unsupported_response_type',
            desc='The authorization server does not support obtaining '
                 'an authorization code using this method.',
        )


class UnsupportedGrantType(OAuthError):
    def __init__(self, desc='The authorization grant type is not supported '
                            'by the authorization server.'):
        super(UnsupportedGrantType, self).__init__(
            code='unsupported_grant_type',
            desc=desc,
        )


class InvalidRedirectURI(OAuthError):
    def __init__(self):
        super(InvalidRedirectURI, self).__init__(
            code='invalid_redirect_uri',
            desc='Invalid redirect URI.',
        )


class InvalidScope(OAuthError):
    def __init__(self):
        super(InvalidScope, self).__init__(
            code='invalid_scope',
            desc='The requested scope is invalid, unknown, or malformed.',
        )


class InvalidClient(OAuthError):
    def __init__(self):
        super(InvalidClient, self).__init__(
            code='invalid_client',
            desc='Client authentication failed.',
        )


class InvalidGrant(OAuthError):
    def __init__(self):
        super(InvalidGrant, self).__init__(
            code='invalid_grant',
            desc='The provided authorization grant or refresh token is invalid, '
                 'expired, revoked, or was issued to another client.',
        )


class InvalidToken(OAuthError):
    def __init__(self):
        super(InvalidToken, self).__init__(
            code='invalid_token',
            desc='The provided authorization token is invalid, expired, '
                 'revoked, or was issued to another client.',
        )


class NotAuthorized(OAuthError):
    def __init__(self):
        super(NotAuthorized, self).__init__(
            code='not_authorized',
            desc='You need to be authorized to access the requested resource',
            status=401,
        )
