from metabrainz import db
import sqlalchemy


def get_all():
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id,
                   name,
                   short_desc,
                   long_desc,
                   price,
                   available,
                   "primary"
              FROM tier
        """))
        return [dict(row._mapping) for row in result.fetchall()]
