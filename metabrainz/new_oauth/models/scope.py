import sqlalchemy.orm
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


def get_scopes(session: sqlalchemy.orm.Session, scope) -> list[OAuth2Scope]:
    """ Given a comma separated scope string return associated scope objects from db """
    scopes = scope.split(",")
    return session.query(OAuth2Scope).filter(OAuth2Scope.name.in_(scopes))
