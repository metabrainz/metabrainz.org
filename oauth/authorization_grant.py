from authlib.oauth2.rfc6749 import grants

from oauth.model import db
from oauth.model.code import OAuth2AuthorizationCode
from oauth.model.scope import get_scopes
from oauth.model.user import User


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):

    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_post"]

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
        )
        db.session.add(auth_code)
        db.session.commit()
        return auth_code

    def query_authorization_code(self, code, client):
        # TODO: Consider adding expiry for auth code
        return db.session\
            .query(OAuth2AuthorizationCode)\
            .filter_by(code=code, client_id=client.id)\
            .first()

    def delete_authorization_code(self, authorization_code):
        db.session.delete(authorization_code)
        db.session.commit()

    def authenticate_user(self, authorization_code):
        return db.session\
            .query(User)\
            .filter_by(id=authorization_code.user_id)\
            .first()
