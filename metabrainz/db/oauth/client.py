from metabrainz import db
from metabrainz.utils import generate_string
import sqlalchemy


def create(name, user_id, desc, website, redirect_uri):
    """Creates new OAuth client and generates a secret key for it.

    Args:
        user_id: ID of a user who manages the client.
        name: Name of the client.
        desc: Client description.
        website: Client web site.
        redirect_uri: URI where responses will be sent.

    Returns:
        New OAuth client ID.
    """
    client_id = generate_string(20)
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO oauth_client (client_id, client_secret, redirect_uri, user_id, name, description, website)
                 VALUES (:client_id, :client_secret, :redirect_uri, :user_id, :name, :description, :website)
        """), {
            "client_id": client_id,
            "client_secret": generate_string(40),
            "redirect_uri": redirect_uri,
            "user_id": user_id,
            "name": name,
            "description": desc,
            "website": website,
        })
    return client_id


def get(client_id):
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT client_id, client_secret, redirect_uri, user_id, name, description, website
              FROM oauth_client
             WHERE client_id = :client_id
        """), {"client_id": client_id})
        row = result.fetchone()
        return dict(row) if row else None
