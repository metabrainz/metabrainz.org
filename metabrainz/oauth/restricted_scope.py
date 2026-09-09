from authlib.oauth2.rfc6749 import InvalidScopeError


class RestrictedScopeMixin:
    """ Refuse requests asking for restricted scopes the client has not been granted.

    Mixed into every grant that validates a requested scope. authlib sets
    ``request.client`` before it calls ``validate_requested_scope()`` in each of them,
    so the check can look at the client the request was made for.

    The refresh token grant does not validate the requested scope at all (it only
    checks it against the scope of the token being refreshed), it is covered by
    ``OAuth2Client.get_allowed_scope`` instead.
    """

    def validate_requested_scope(self):
        super().validate_requested_scope()

        client = self.request.client
        if client is None:
            return

        disallowed = client.disallowed_scopes(self.request.payload.scope)
        if disallowed:
            # the state is deliberately not set here: the token endpoint error
            # response has no state member and the authorization server fills the
            # state in itself for the errors it turns into a redirect
            raise InvalidScopeError(
                description="The client is not allowed to request the following scopes: "
                            + ", ".join(disallowed),
            )
