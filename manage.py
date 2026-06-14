import urllib.parse
import subprocess
import os
import click
import logging

from werkzeug.serving import run_simple

from metabrainz import db
from metabrainz import create_app
from metabrainz.model.access_log import AccessLog
from metabrainz.invoices.send_invoices import QuickBooksInvoiceSender
from metabrainz.webhooks.cli import webhooks

from metabrainz.supporter.copy_mb_row_ids import copy_row_ids
from metabrainz.user.migrate_mb_users import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CLEARTEXT_PASSWORD_LOG_ROUNDS,
    migrate_mb_users,
)

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'admin', 'sql')

cli = click.Group()
application = create_app()

cli.add_command(webhooks)


def _configure_cli_logging(app, level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger().setLevel(level)
    app.logger.setLevel(level)


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
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'oauth', 'create_tables.sql'))
    click.echo('Done.')

    click.echo('Creating primary and foreign keys... ', nl=False)
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'oauth', 'create_primary_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'oauth', 'create_foreign_keys.sql'))
    click.echo('Done.')

    click.echo('Creating indexes... ', nl=False)
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'oauth', 'create_indexes.sql'))
    click.echo('Done.')

    click.echo("Database has been initialized successfully!")


@cli.command()
def extract_strings():
    """Extract all strings into messages.pot.
    This command should be run after any translatable strings are updated.
    Otherwise updates are not going to be available on Weblate.
    """
    _run_command("pybabel extract -F metabrainz/babel.cfg -k t "
                 "--project=metabrainz.org "
                 "--copyright-holder='MetaBrainz Foundation' "
                 "--msgid-bugs-address=support@metabrainz.org "
                 "-o metabrainz/messages.pot "
                 "metabrainz/ frontend/js/src/")
    click.echo("Strings have been successfully extracted into messages.pot file.")


@cli.command()
def compile_translations():
    """Compile the backend translation catalogs (.mo files for Flask-Babel)."""
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


@cli.command()
def import_musicbrainz_row_ids():
    """ Import musicbrainz row ids for users """
    with create_app().app_context():
        copy_row_ids()


@cli.command()
@click.option("--batch-size", "-b", default=DEFAULT_BATCH_SIZE, show_default=True,
              help="Number of editors to migrate per batch.")
@click.option("--cleartext-password-log-rounds", default=DEFAULT_CLEARTEXT_PASSWORD_LOG_ROUNDS,
              type=click.IntRange(4, 31),
              show_default=True,
              help="Bcrypt log rounds for MusicBrainz {CLEARTEXT} passwords.")
def migrate_musicbrainz_users(batch_size, cleartext_password_log_rounds):
    """ Migrate users from the MusicBrainz editor table into the MetaBrainz user table. """
    app = create_app()
    _configure_cli_logging(app)
    with app.app_context():
        migrate_mb_users(
            batch_size=batch_size,
            cleartext_password_log_rounds=cleartext_password_log_rounds,
        )


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
