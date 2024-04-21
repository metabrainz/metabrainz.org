from authlib.oauth2.rfc6749 import grants, InvalidGrantError

from oauth import login
from oauth.model import db, OAuth2AccessToken, OAuth2RefreshToken
from oauth.model.code import OAuth2AuthorizationCode
from oauth.model.scope import get_scopes


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):

    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_basic", "client_secret_post"]

    def save_authorization_code(self, code, request):
        code_challenge = request.data.get("code_challenge")
        code_challenge_method = request.data.get("code_challenge_method")

        scopes = get_scopes(db.session, request.scope)

        auth_code = OAuth2AuthorizationCode(
            code=code,
            client_id=request.client.id,
            redirect_uri=request.redirect_uri,
            scopes=scopes,
            user_id=request.user.id,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            expires_in=600,  # todo: make configurable like other oauth2_ options
        )
        db.session.add(auth_code)
        db.session.commit()
        return auth_code

    def query_authorization_code(self, code, client):
        authorization_code = db.session\
            .query(OAuth2AuthorizationCode)\
            .filter_by(code=code, client_id=client.id)\
            .first()

        if authorization_code is None:
            return None

        if authorization_code.is_expired():
            raise InvalidGrantError("\"code\" in request is expired.")

        # authorization code is already used, revoke tokens previously issued based on this code in compliance with
        # Section 4.1.2 of RFC 6749
        if authorization_code.revoked:
            db.session.query(OAuth2AccessToken).filter_by(
                authorization_code_id=authorization_code.id,
                client_id=client.id
            ).update({OAuth2AccessToken.revoked: True})
            db.session.query(OAuth2RefreshToken).filter_by(
                authorization_code_id=authorization_code.id,
                client_id=client.id
            ).update({OAuth2RefreshToken.revoked: True})
            db.session.commit()

            raise InvalidGrantError("\"code\" in request is already used.")

        return authorization_code

    def delete_authorization_code(self, authorization_code):
        authorization_code.revoked = True
        db.session.commit()

    def authenticate_user(self, authorization_code):
        return login.load_user_from_db(authorization_code.user_id)
