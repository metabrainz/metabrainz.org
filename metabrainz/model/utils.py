from urlparse import urlsplit
from sqlalchemy import create_engine
from metabrainz.model import db
import subprocess


def create_tables(db_uri):
    engine = create_engine(db_uri)
    db.metadata.create_all(engine)


def init_postgres(db_uri):
    """Initializes PostgreSQL database from provided URI.
    New user and database will be created, if needed. It also creates uuid-ossp extension.
    """
    hostname, port, db, username, password = _split_db_uri(db_uri)
    if hostname not in ['localhost', '127.0.0.1']:
        raise Exception('Cannot configure a remote database')

    # Checking if user already exists
    retv = subprocess.check_output('sudo -u postgres psql -t -A -c "SELECT COUNT(*) FROM pg_user WHERE usename = \'%s\';"' % username, shell=True)
    if retv[0] == '0':
        exit_code = subprocess.call('sudo -u postgres psql -c "CREATE ROLE %s PASSWORD \'%s\' NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT LOGIN;"' % (username, password), shell=True)
        if exit_code != 0:
            raise Exception('Failed to create PostgreSQL user!')

    # Checking if database exists
    exit_code = subprocess.call('sudo -u postgres psql -c "\q" %s' % db, shell=True)
    if exit_code != 0:
        exit_code = subprocess.call('sudo -u postgres createdb -O %s %s' % (username, db), shell=True)
        if exit_code != 0:
            raise Exception('Failed to create PostgreSQL database!')


def _split_db_uri(uri):
    """Extracts database connection info from the URI.

    Returns:
        Tuple: hostname, port, database name, username and password.
    """
    uri = urlsplit(uri)
    return uri.hostname, uri.port, uri.path[1:], uri.username, uri.password
