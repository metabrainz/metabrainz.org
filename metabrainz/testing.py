from flask_testing import TestCase
from metabrainz import create_app
from metabrainz import model
from metabrainz import db
import logging
import os.path
import os

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'admin', 'sql')


class FlaskTestCase(TestCase):

    def create_app(self):
        app = create_app(config_path=os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            '..', 'config.py'
        ))
        app.config['TESTING'] = True
        db.init_db_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        return app

    def setUp(self):
        logging.basicConfig(level=logging.DEBUG)
        self.reset_db()

    def tearDown(self):
        model.db.session.remove()

    def temporary_login(self, user_id):
        with self.client.session_transaction() as session:
            session['user_id'] = user_id
            session['_fresh'] = True

    def reset_db(self):
        self.drop_tables()
        self.init_db()

    def init_db(self):
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    def drop_tables(self):
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'drop_tables.sql'))
