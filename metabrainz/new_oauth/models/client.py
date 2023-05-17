from authlib.oauth2.rfc6749 import ClientMixin
from sqlalchemy import Column, Text, ForeignKey, Integer, ARRAY, Identity, DateTime, func
from sqlalchemy.orm import relationship


from metabrainz.model import db


class OAuth2Client(db.Model, ClientMixin):

    __tablename__ = 'client'
    __table_args__ = {
        'schema': 'oauth'
    }

    id = Column(Integer, Identity(), primary_key=True)
    client_id = Column(Text, nullable=False)
    client_secret = Column(Text)
    owner_id = Column(Integer, ForeignKey('oauth.user.id', ondelete='CASCADE'), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    website = Column(Text)
    redirect_uris = Column(ARRAY(Text), nullable=False)
    client_id_issued_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    user = relationship('OAuth2User')

    def get_client_id(self):
        return self.client_id

    def get_default_redirect_uri(self):
        if self.redirect_uris:
            return self.redirect_uris[0]
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
        return True  # TODO: Fix response types

    def check_grant_type(self, grant_type):
        return True  # TODO: Fix grant types
