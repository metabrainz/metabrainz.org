from authlib.oauth2.rfc6749 import ClientMixin
from sqlalchemy import Column, Text, ForeignKey, Integer, ARRAY, Identity, DateTime, func
from sqlalchemy.orm import relationship


from metabrainz.new_oauth.models import Base


class OAuth2Client(Base, ClientMixin):

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
        pass

    def get_default_redirect_uri(self):
        pass

    def get_allowed_scope(self, scope):
        pass

    def check_redirect_uri(self, redirect_uri):
        pass

    def has_client_secret(self):
        pass

    def check_client_secret(self, client_secret):
        pass

    def check_token_endpoint_auth_method(self, method):
        pass

    def check_response_type(self, response_type):
        pass

    def check_grant_type(self, grant_type):
        pass
