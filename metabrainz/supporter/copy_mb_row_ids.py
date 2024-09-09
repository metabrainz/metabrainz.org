import psycopg2
from psycopg2.extras import execute_values
from flask import current_app

from metabrainz import db

mb_db_conn = "postgresql://musicbrainz_ro@10.2.2.25:65437/musicbrainz_db"


def copy_row_ids():
    current_app.logger.info("Beginning to update emails for users...")
    connection = db.engine.raw_connection()
    try:
        with (connection.cursor() as cursor,
              psycopg2.connect(mb_db_conn) as mb_connection,
              mb_connection.cursor() as mb_curs):
            cursor.execute("SELECT musicbrainz_id FROM supporter")
            editor_ids = [(row[0],) for row in cursor.fetchall()]
            current_app.logger.info("Fetched musicbrainz ids from MeB.")

            results = execute_values(mb_curs, """
                SELECT id, name
                  FROM editor e
                 WHERE EXISTS(
                        SELECT 1
                          FROM (VALUES %s) AS t(user_id)
                         WHERE t.user_id = e.user_id
                 )
            """, editor_ids, fetch=True)
            editors = [(r[0], r[1]) for r in results]
            current_app.logger.info("Fetched editor emails from MusicBrainz.")

            query = """
                UPDATE supporter s
                   SET musicbrainz_row_id = t.musicbrainz_row_id
                  FROM (VALUES %s) AS t(musicbrainz_row_id, musicbrainz_id)
                WHERE s.musicbrainz_id = t.musicbrainz_id
            """
            execute_values(cursor, query, editors)
            current_app.logger.info("Updated row ids of supporters.")
        connection.commit()
    except psycopg2.errors.OperationalError:
        current_app.logger.error("Error while updating emails of MetaBrainz supporters", exc_info=True)
        connection.rollback()
    finally:
        connection.close()
