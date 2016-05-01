from metabrainz import db
from metabrainz.db import oauth
import sqlalchemy


def create(client_id, user_id, redirect_uri, code, expires, scopes=None):
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            INSERT INTO oauth_grant (client_id, user_id, redirect_uri, code, expires, scopes)
                 VALUES (:client_id, :user_id, :redirect_uri, :code, :expires, :scopes)
              RETURNING id
        """), {
            "client_id": client_id,
            "user_id": user_id,
            "redirect_uri": redirect_uri,
            "code": code,
            "expires": expires,
            "scopes": oauth.scopes_list_to_string(scopes),
        })
        return result.fetchone()["id"]


def get(client_id, code):
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, client_id, user_id, redirect_uri, code, expires, scopes
              FROM oauth_grant
             WHERE client_id = :client_id AND code = :code
        """), {
            "client_id", client_id,
            "code", code,
        })
        row = result.fetchone()
        if row:
            out = dict(row)
            out["scopes"] = oauth.scopes_string_to_list(out["scopes"])
            return out
        else:
            return None


def delete_by_code(client_id, code):
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE FROM oauth_grant
                  WHERE client_id = :client_id AND code = :code
        """), {
            "client_id", client_id,
            "code", code,
        })
