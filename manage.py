from werkzeug.serving import run_simple
from metabrainz import db
from metabrainz import create_app
from metabrainz.model.access_log import AccessLog
from metabrainz.invoices.send_invoices import QuickBooksInvoiceSender
import urllib.parse
import subprocess
import os
import click

import logging

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
    db.init_db_engine(application.config["POSTGRES_ADMIN_URI"])

    if force:
        click.echo('Dropping existing database... ', nl=False)
        db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'drop_db.sql'))
        click.echo('Done.')

    if create_db:
        click.echo('Creating user and a database... ', nl=False)
        db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'create_db.sql'))
        click.echo('Done.')

        click.echo('Creating database extensions... ', nl=False)
        db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'create_extensions.sql'))
        click.echo('Done.')

    db.init_db_engine(application.config["SQLALCHEMY_DATABASE_URI"])

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
def compile_translations():
    """Compile translations for use."""
    _run_command("pybabel compile -d metabrainz/translations")
    click.echo("Translated strings have been compiled and ready to be used.")


@cli.command()
def cleanup_logs():
    with create_app().app_context():
        AccessLog.remove_old_ip_addr_records()


@cli.command()
def send_invoices():
    """ Send invoices that are prepared, but unsent in QuickBooks."""

    with create_app().app_context():
        qb = QuickBooksInvoiceSender()
        qb.send_invoices()


@cli.command()
def send_invoice_reminders():
    """ Send invoices reminders about invoices that remain unpaid."""

    logging.getLogger().setLevel(logging.DEBUG)
    with create_app().app_context():
        qb = QuickBooksInvoiceSender()
        qb.send_invoice_reminders()


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

"""
insert into tier (name, short_desc, long_desc, price, available, "primary") values ('We will contribute, we promise!', 'For lame user lying about supporting us.', 'Whatevs, you dont care anyway.', 0.0, 't', 't');
"""