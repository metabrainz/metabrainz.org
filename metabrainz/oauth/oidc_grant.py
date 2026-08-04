from authlib.oidc.core import grants, UserInfo
from authlib.oauth2.rfc6749.util import scope_to_list
from flask import current_app

from metabrainz.model import db, OAuth2AuthorizationCode, OAuth2Client


def build_user_info(user, scope, include_member_since=False):
    user_info = UserInfo(
        sub=str(user.id),
        username=user.name,
    )

    if include_member_since:
        user_info["member_since"] = user.member_since.isoformat() if user.member_since else None

    granted_scopes = set(scope_to_list(scope) or [])
    if "email" in granted_scopes:
        email = user.get_email_any()
        if email:
            user_info["email"] = email
            user_info["email_verified"] = user.is_email_confirmed()

    return user_info


class OpenIDCodeMixin:

    def exists_nonce(self, nonce, request):
        exists = db.session \
            .query(OAuth2AuthorizationCode) \
            .join(OAuth2Client) \
            .filter(
                OAuth2Client.client_id == request.payload.client_id,
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
        return build_user_info(user, scope)


class OpenIDCode(OpenIDCodeMixin, grants.OpenIDCode):

    def get_jwt_config(self, grant):
        return self._get_jwt_config()


class OpenIDImplicitGrant(OpenIDCodeMixin, grants.OpenIDImplicitGrant):

    def get_jwt_config(self):
        return self._get_jwt_config()
