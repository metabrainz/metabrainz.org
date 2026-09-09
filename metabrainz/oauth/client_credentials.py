from authlib.oauth2.rfc6749 import grants

from metabrainz.oauth.restricted_scope import RestrictedScopeMixin


class ClientCredentialsGrant(RestrictedScopeMixin, grants.ClientCredentialsGrant):

    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_basic", "client_secret_post"]
