from authlib.oauth2.rfc6749 import grants

from metabrainz.new_oauth.models import db
from metabrainz.new_oauth.models.code import OAuth2AuthorizationCode
from metabrainz.new_oauth.models.scope import get_scopes
from metabrainz.new_oauth.models.user import OAuth2User


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):

    TOKEN_ENDPOINT_AUTH_METHODS = ['none', 'client_secret_post']

    def save_authorization_code(self, code, request):
        client = request.client

        code_challenge = request.data.get('code_challenge')
        code_challenge_method = request.data.get('code_challenge_method')

        scopes = get_scopes(db.session, request.scope)

        auth_code = OAuth2AuthorizationCode(
            code=code,
            client_id=client.client_id,
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
        item = db.session\
            .query(OAuth2AuthorizationCode)\
            .filter_by(code=code, client_id=client.client_id)\
            .first()
        if item and not item.is_expired():
            return item

    def delete_authorization_code(self, authorization_code):
        db.session.delete(authorization_code)
        db.session.commit()

    def authenticate_user(self, authorization_code):
        # TODO: fix authenticate_user
        # return db.session\
        #     .query(OAuth2User)\
        #     .filter_by(user_id=authorization_code.user_id)
        pass
