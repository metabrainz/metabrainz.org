from __future__ import print_function
from werkzeug.serving import run_simple
from metabrainz import db
from metabrainz import create_app
from metabrainz.model.access_log import AccessLog
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
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
@click.option("--skip-create-db", "-s", is_flag=True,
              help="Skip database creation step.")
def init_db(force=False, skip_create_db=False):
    if force:
        exit_code = _run_psql('drop_db.sql')
        if exit_code != 0:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    if not skip_create_db:
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


@cli.command()
def extract_strings():
    """Extract all strings into messages.pot.
    This command should be run after any translatable strings are updated.
    Otherwise updates are not going to be available on Transifex.
    """
    _run_command("pybabel extract -F metabrainz/babel.cfg "
                 "-o metabrainz/messages.pot metabrainz/")
    click.echo("Strings have been successfully extracted into messages.pot file.")


@cli.command()
def compile_translations():
    """Compile translations for use."""
    _run_command("pybabel compile -d metabrainz/translations")
    click.echo("Translated strings have been compiled and ready to be used.")


@cli.command()
def cleanup_logs():
    with create_app().app_context():
        AccessLog.remove_old_ip_addr_records()


def _run_psql(script, database=None):
    script = os.path.join(ADMIN_SQL_DIR, script)
    command = ['psql', '-p', str(application.config["PG_PORT"]), '-U', application.config["PG_SUPER_USER"], '-f', script]
    if database:
        command.extend(['-d', database])
    return subprocess.call(command)


def _run_command(command):
    return subprocess.check_call(command, shell=True)

if __name__ == '__main__':
    cli()
