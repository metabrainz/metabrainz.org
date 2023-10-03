import sqlalchemy.orm
from authlib.oauth2.rfc6749.util import scope_to_list
from sqlalchemy import Integer, Text
from sqlalchemy.sql.schema import Identity, Column

from metabrainz.model import db


class OAuth2Scope(db.Model):
    __tablename__ = 'scope'
    __table_args__ = {
        'schema': 'oauth'
    }

    id = Column(Integer, Identity(), primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=False)


def get_scopes(session: sqlalchemy.orm.Session, scope):
    """ Given a comma separated scope string return associated scope objects from db """
    scopes = scope_to_list(scope)
    # TODO: error if unknown scopes requested ?
    return session.query(OAuth2Scope).filter(OAuth2Scope.name.in_(scopes)).all()
