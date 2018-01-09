from werkzeug.serving import run_simple
from metabrainz import db
from metabrainz import create_app
from metabrainz.model.access_log import AccessLog
import urllib.parse
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
@click.option("--create-db", "-c", is_flag=True, help="Create database and extensions.")
def init_db(force=False, create_db=False):
    db_uri = application.config["SQLALCHEMY_DATABASE_URI"]

    if force:
        click.echo('Dropping existing database... ', nl=False)
        exit_code = _run_psql('drop_db.sql', db_uri)
        if exit_code != 0:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)
        click.echo('Done.')

    if create_db:

        click.echo('Creating user and a database... ', nl=False)
        exit_code = _run_psql('create_db.sql', db_uri)
        if exit_code != 0:
            raise Exception('Failed to create new database and user! Exit code: %i' % exit_code)
        click.echo('Done.')

        click.echo('Creating database extensions... ', nl=False)
        exit_code = _run_psql('create_extensions.sql', db_uri, database='metabrainz')
        if exit_code != 0:
            raise Exception('Failed to create database extensions! Exit code: %i' % exit_code)
        click.echo('Done.')

    db.init_db_engine(db_uri)

    click.echo('Creating types... ', nl=False)
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_types.sql'))
    click.echo('Done.')

    click.echo('Creating tables... ', nl=False)
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
    click.echo('Done.')

    click.echo('Creating primary and foreign keys... ', nl=False)
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
    click.echo('Done.')

    click.echo('Creating indexes... ', nl=False)
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))
    click.echo('Done.')

    click.echo("Database has been initialized successfully!")


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
def pull_translations():
    """Pull translations for languages defined in config from Transifex and compile them.
    Before using this command make sure that you properly configured Transifex client.
    More info about that is available at http://docs.transifex.com/developer/client/setup#configuration.
    """
    languages = ','.join(create_app().config['SUPPORTED_LANGUAGES'])
    _run_command("tx pull -f -r metabrainz.metabrainz -l %s" % languages)


@cli.command()
def update_strings():
    """Extract strings and pull translations from Transifex."""
    extract_strings()
    pull_translations()
    
@cli.command()
def compile_translations():
    """Compile translations for use."""
    _run_command("pybabel compile -d metabrainz/translations")
    click.echo("Translated strings have been compiled and ready to be used.")


@cli.command()
def cleanup_logs():
    with create_app().app_context():
        AccessLog.remove_old_ip_addr_records()


def _run_psql(script, uri, database=None):
    hostname, port, db_name, username, password = _explode_db_uri(uri)
    script = os.path.join(ADMIN_SQL_DIR, script)
    command = [
        'psql',
        '-h', hostname,
        '-p', str(port),
        '-U', username,
        '-f', script,
    ]
    if database:
        command.extend(['-d', database])
    return subprocess.call(command)


def _run_command(command):
    return subprocess.check_call(command, shell=True)


def _explode_db_uri(uri):
    """Extracts database connection info from the URI.
    Returns hostname, database name, username and password.
    """
    uri = urllib.parse.urlsplit(uri)
    return uri.hostname, uri.port, uri.path[1:], uri.username, uri.password


if __name__ == '__main__':
    cli()
