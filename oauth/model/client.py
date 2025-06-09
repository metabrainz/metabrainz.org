from authlib.oauth2.rfc6749 import ClientMixin
from flask import current_app
from sqlalchemy import Column, Text, Integer, ARRAY, Identity, DateTime, func

from oauth.model import db


class OAuth2Client(db.Model, ClientMixin):

    __tablename__ = "client"
    __table_args__ = {
        "schema": "oauth"
    }

    id = Column(Integer, Identity(), primary_key=True)
    client_id = Column(Text, nullable=False)
    client_secret = Column(Text)
    # no FK to user table because user data lives in MB db
    owner_id = Column(Integer, nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    website = Column(Text)
    redirect_uris = Column(ARRAY(Text), nullable=False)
    client_id_issued_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    def get_client_id(self):
        return self.client_id

    def get_default_redirect_uri(self):
        return None

    def get_allowed_scope(self, scope):
        pass  # TODO: Fix allowed scopes

    def check_redirect_uri(self, redirect_uri):
        return redirect_uri in self.redirect_uris

    def has_client_secret(self):
        return bool(self.client_secret)

    def check_client_secret(self, client_secret):
        return self.client_secret == client_secret

    def check_endpoint_auth_method(self, method, endpoint):
        return True  # TODO: Fix token endpoint auth

    def check_response_type(self, response_type):
        return True  # TODO: Fix check response type

    def check_grant_type(self, grant_type):
        if grant_type == "client_credentials":
            return self.client_id in current_app.config.get("OAUTH2_WHITELISTED_CCG_CLIENTS", [])
        return True

    def check_already_approved(self, user_id, requested_scopes):
        """ Check if the user has previously approved all the scopes for a given client """
        from oauth.model.access_token import OAuth2AccessToken

        requested_scopes = {s.name for s in requested_scopes}
        tokens = db.session.query(OAuth2AccessToken).filter_by(client_id=self.id, user_id=user_id, revoked=False).all()
        for token in tokens:
            existing_scopes = {s.name for s in token.scopes}
            if existing_scopes.issuperset(requested_scopes):
                return True
        return False
