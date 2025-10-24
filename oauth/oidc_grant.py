from authlib.oidc.core import grants, UserInfo
from flask import current_app

from oauth.model import OAuth2Client, db
from oauth.model.code import OAuth2AuthorizationCode


class OpenIDCodeMixin:

    def exists_nonce(self, nonce, request):
        exists = db.session \
            .query(OAuth2AuthorizationCode) \
            .join(OAuth2Client) \
            .filter(
                OAuth2Client.client_id == request.client_id,
                OAuth2AuthorizationCode.nonce == nonce,
            ).first()
        return bool(exists)

    def _get_jwt_config(self):
        return {
            "key": current_app.config["OIDC_JWT_PRIVATE_KEY"],
            "iss": "https://metabrainz.org",
            "alg": "ES256",
            "exp": current_app.config["OIDC_ID_TOKEN_EXPIRATION"],
        }

    def generate_user_info(self, user, scope):
        user_info = UserInfo(sub=user.id, name=user.name)
        return user_info


class OpenIDCode(OpenIDCodeMixin, grants.OpenIDCode):

    def get_jwt_config(self, grant):
        return self._get_jwt_config()


class OpenIDImplicitGrant(OpenIDCodeMixin, grants.OpenIDImplicitGrant):

    def get_jwt_config(self):
        return self._get_jwt_config()
