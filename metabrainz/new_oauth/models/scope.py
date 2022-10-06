from sqlalchemy import Integer, Text
from sqlalchemy.sql.schema import Identity, Column

from metabrainz.new_oauth.models import Base


class OAuth2Scope(Base):
    __tablename__ = 'scope'
    __table_args__ = {
        'schema': 'oauth'
    }

    id = Column(Integer, Identity(), primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
