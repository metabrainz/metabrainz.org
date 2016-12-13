from __future__ import print_function
from werkzeug.serving import run_simple
from metabrainz import db
from metabrainz import create_app
from metabrainz.model.access_log import AccessLog
from metabrainz.model.utils import init_postgres, create_tables as db_create_tables
import subprocess
import os
import click

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'admin', 'sql')

cli = click.Group()
application = create_app()


@cli.command()
@click.option("--host", "-h", default="0.0.0.0", show_default=True)
@click.option("--port", "-p", default=8080, show_default=True)
@click.option("--debug", "-d", is_flag=True,
              help="Turns debugging mode on or off. If specified, overrides "
                   "'DEBUG' value in the config file.")
def runserver(host, port, debug=False):
    run_simple(
        hostname=host,
        port=port,
        application=application,
        use_debugger=debug,
        use_reloader=debug,
    )


@cli.command()
def create_db():
    """Create and configure the database."""
    with application.app_context():
        init_postgres(application.config['SQLALCHEMY_DATABASE_URI'])

@cli.command()
@click.option("--host", "-h", default="0.0.0.0", show_default=True)
@click.option("--port", "-p", default=8080, show_default=True)
@click.option("--debug", "-d", is_flag=True,
              help="Turns debugging mode on or off. If specified, overrides "
                   "'DEBUG' value in the config file.")
def runserver(host, port, debug):
    create_app().run(host=host, port=port, debug=debug)

@cli.command()
def create_tables():
    with application.app_context():
        db_create_tables(application.config['SQLALCHEMY_DATABASE_URI'])

def _run_psql(script, database=None):
    script = os.path.join(ADMIN_SQL_DIR, script)
    command = ['psql', '-p', str(application.config["PG_PORT"]), '-U', application.config["PG_SUPER_USER"], '-f', script]
    if database:
        command.extend(['-d', database])
    return subprocess.call(command)

@cli.command()
def cleanup_logs():
    with create_app().app_context():
        AccessLog.remove_old_ip_addr_records()

@cli.command()
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
def init_db(force):
    if force:
        exit_code = _run_psql('drop_db.sql')
        if exit_code != 0:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    print('Creating user and a database...')
    exit_code = _run_psql('create_db.sql')
    if exit_code != 0:
        raise Exception('Failed to create new database and user! Exit code: %i' % exit_code)

    print('Creating database extensions...')
    exit_code = _run_psql('create_extensions.sql', 'metabrainz')
    if exit_code != 0:
        raise Exception('Failed to create database extensions! Exit code: %i' % exit_code)

    db.init_db_engine(application.config["SQLALCHEMY_DATABASE_URI"])

    print('Creating types...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_types.sql'))

    print('Creating tables...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))

    print('Creating primary and foreign keys...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))

    print('Creating indexes...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    print("Done!")


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
def init_test_db(force=False):
    """Same as `init_db` command, but creates a database that will be used to
    run tests.

    `SQLALCHEMY_DATABASE_URI` must be defined in the config file.
    """
    if force:
        exit_code = _run_psql('drop_test_db.sql')
        if exit_code != 0:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    print('Creating database and user for testing...')
    exit_code = _run_psql('create_test_db.sql')
    if exit_code != 0:
        raise Exception('Failed to create new database and user! Exit code: %i' % exit_code)

    exit_code = _run_psql('create_extensions.sql', 'meb_test')
    if exit_code != 0:
        raise Exception('Failed to create database extensions! Exit code: %i' % exit_code)

    db.init_db_engine(application.config["SQLALCHEMY_DATABASE_URI"])

    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_types.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    print("Done!")


if __name__ == '__main__':
    cli()
