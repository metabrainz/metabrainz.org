from authlib.oauth2.rfc6749 import ClientMixin
from sqlalchemy import Column, Text, ForeignKey, Integer, ARRAY, Identity
from sqlalchemy.orm import relationship


from metabrainz.new_oauth.models import Base


class OAuth2Client(Base, ClientMixin):

    __tablename__ = 'oauth2_client'

    id = Column(Integer, Identity(), primary_key=True)
    client_id = Column(Text, nullable=False)
    client_secret = Column(Text)
    owner_id = Column(Integer, ForeignKey('oauth.user.id', ondelete='CASCADE'), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    website = Column(Text)
    redirect_uris = Column(ARRAY(Text), nullable=False)

    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'))
    user = relationship('OAuth2User')
