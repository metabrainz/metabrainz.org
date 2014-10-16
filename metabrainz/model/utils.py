from urlparse import urlsplit
import subprocess


def explode_db_url(url):
    """Extracts database connection info from the URL.

    Returns:
        hostname, database name, username and password
    """
    url = urlsplit(url)
    return url.hostname, url.path[1:], url.username, url.password


def init_postgres(uri):
    """Initializes PostgreSQL database from provided URI.
    New user and database will be created, if needed.
    """
    hostname, db, username, password = explode_db_url(uri)
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
