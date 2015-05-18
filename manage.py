from flask_script import Manager
from flask import current_app
from metabrainz import create_app
from metabrainz.model.access_log import AccessLog
from metabrainz.model.utils import init_postgres, create_tables as db_create_tables

manager = Manager(create_app)


@manager.command
def create_db():
    """Create and configure the database."""
    init_postgres(current_app.config['SQLALCHEMY_DATABASE_URI'])


@manager.command
def create_tables():
    db_create_tables(current_app.config['SQLALCHEMY_DATABASE_URI'])


@manager.command
def cleanup_logs():
    with create_app().app_context():
        AccessLog.remove_old_ip_addr_records()


if __name__ == '__main__':
    manager.run()
