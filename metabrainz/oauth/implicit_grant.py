from urllib.parse import urlparse, parse_qs

from authlib.oauth2.rfc6749 import grants, InvalidRequestError
from flask import render_template


class ImplicitGrant(grants.ImplicitGrant):

    def validate_authorization_request(self):
        result = super().validate_authorization_request()

        response_mode = self.request.payload.data.get("response_mode")
        if response_mode and response_mode != "form_post":
            raise InvalidRequestError("Invalid 'response_mode' in request.", state=self.request.state)

        return result

    def create_authorization_response(self, redirect_uri, grant_user):
        response = super().create_authorization_response(redirect_uri, grant_user)

        if self.request.payload.data.get("response_mode") == "form_post":
            headers = response[2]
            location = headers[0][1]
            parsed = urlparse(location)
            query = parse_qs(parsed.fragment)
            return 200, render_template(
                "oauth/authorize_form_post.html",
                values=query,
                redirect_uri=redirect_uri,
            ), []

        return response
