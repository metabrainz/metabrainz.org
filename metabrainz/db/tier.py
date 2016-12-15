from metabrainz import db


def get_all():
    with db.engine.connect() as connection:
        result = connection.execute("""
            SELECT id,
                   name,
                   short_desc,
                   long_desc,
                   price,
                   available,
                   "primary"
              FROM tier
        """)
        return result.fetchall()
