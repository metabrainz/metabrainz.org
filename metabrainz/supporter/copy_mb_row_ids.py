import psycopg2
from psycopg2.extras import execute_values
from flask import current_app

from metabrainz import db

mb_db_conn = "postgresql://musicbrainz_ro@10.2.2.25:65437/musicbrainz_db"


def copy_row_ids_for_table(table_name, fetch_query, update_query):
    current_app.logger.info(f"Beginning to update emails for {table_name}")
    connection = db.engine.raw_connection()
    try:
        with (connection.cursor() as cursor,
              psycopg2.connect(mb_db_conn) as mb_connection,
              mb_connection.cursor() as mb_curs):
            cursor.execute(fetch_query)
            editor_ids = [(row[0],) for row in cursor.fetchall()]
            current_app.logger.info("Fetched musicbrainz ids from MeB.")

            results = execute_values(mb_curs, """
                SELECT id, name
                  FROM editor e
                 WHERE EXISTS(
                        SELECT 1
                          FROM (VALUES %s) AS t(username)
                         WHERE lower(t.username) = lower(e.name)
                 )
            """, editor_ids, fetch=True)
            editors = [(r[0], r[1]) for r in results]
            current_app.logger.info("Fetched editor emails from MusicBrainz.")

            execute_values(cursor, update_query, editors)
            current_app.logger.info(f"Updated row ids of {table_name}.")
        connection.commit()
    except psycopg2.errors.OperationalError:
        current_app.logger.error(f"Error while updating musicbrainz row ids in {table_name}", exc_info=True)
        connection.rollback()
    finally:
        connection.close()


def copy_row_ids():
    supporter_fetch_query = "SELECT musicbrainz_id FROM supporter WHERE musicbrainz_row_id IS NULL"
    supporter_update_query = """
        UPDATE supporter s
           SET musicbrainz_row_id = t.musicbrainz_row_id
          FROM (VALUES %s) AS t(musicbrainz_row_id, musicbrainz_id)
        WHERE lower(s.musicbrainz_id) = lower(t.musicbrainz_id)
    """

    payment_fetch_query = "SELECT DISTINCT editor_name FROM payment WHERE editor_name IS NOT NULL AND editor_id IS NULL"
    payment_update_query = """
        UPDATE payment p
           SET editor_id = t.musicbrainz_row_id
          FROM (VALUES %s) AS t(musicbrainz_row_id, musicbrainz_id)
         WHERE lower(p.editor_name) = lower(t.musicbrainz_id)
    """

    copy_row_ids_for_table("supporter", supporter_fetch_query, supporter_update_query)
    copy_row_ids_for_table("payment", payment_fetch_query, payment_update_query)
