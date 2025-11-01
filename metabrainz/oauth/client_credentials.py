from authlib.oauth2.rfc6749 import grants


class ClientCredentialsGrant(grants.ClientCredentialsGrant):

    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_basic", "client_secret_post"]
