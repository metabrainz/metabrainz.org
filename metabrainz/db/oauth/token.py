from metabrainz import db
from metabrainz.db import oauth
import sqlalchemy


def create(client_id, access_token, user_id, refresh_token, expires, scopes=None):
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            INSERT INTO oauth_token (client_id, access_token, user_id, refresh_token, expires, scopes)
                 VALUES (:client_id, :access_token, :user_id, :refresh_token, :expires, :scopes)
              RETURNING id
        """), {
            "client_id": client_id,
            "access_token": access_token,
            "user_id": user_id,
            "redirect_uri": refresh_token,
            "expires": expires,
            "scopes": oauth.scopes_list_to_string(scopes),
        })
    return result.fetchone()["id"]


def get_by_token(access_token):
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, client_id, access_token, user_id, refresh_token, expires, scopes
              FROM oauth_token
             WHERE access_token = :access_token
        """), {"access_token", access_token})
        row = result.fetchone()
        if row:
            out = dict(row)
            out["scopes"] = oauth.scopes_string_to_list(out["scopes"])
            return out
        else:
            return None


def get_by_client_id_and_refresh_token(client_id, refresh_token):
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, client_id, access_token, user_id, refresh_token, expires, scopes
              FROM oauth_token
             WHERE client_id = :client_id AND refresh_token = :refresh_token
        """), {
            "client_id": client_id,
            "refresh_token": refresh_token,
        })
        row = result.fetchone()
        if row:
            out = dict(row)
            out["scopes"] = oauth.scopes_string_to_list(out["scopes"])
            return out
        else:
            return None


def delete_by_refresh_token(client_id, refresh_token):
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE FROM oauth_grant
                  WHERE client_id = :client_id AND refresh_token = :refresh_token
        """), {
            "client_id": client_id,
            "refresh_token": refresh_token,
        })


def delete_by_user_id(client_id, user_id):
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE FROM oauth_grant
                  WHERE client_id = :client_id AND user_id = :user_id
        """), {
            "client_id": client_id,
            "user_id": user_id,
        })
