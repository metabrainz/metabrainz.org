from flask_testing import TestCase
from metabrainz import create_app
from metabrainz import model
from metabrainz import db
import os.path
import os

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'admin', 'sql')



class FlaskTestCase(TestCase):

    def create_app(self):
        app = create_app(config_path=os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'test_config.py'
        ))
        db.init_db_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        return app

    def setUp(self):
        self.reset_db()

    def tearDown(self):
        model.db.session.remove()

    def temporary_login(self, user_id):
        with self.client.session_transaction() as session:
            session['user_id'] = user_id
            session['_fresh'] = True

    def reset_db(self):
        self.drop_tables()
        self.drop_types()
        self.init_db()

    def init_db(self):
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_types.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    def drop_tables(self):
        with db.engine.connect() as connection:
            # TODO(roman): See if there's a better way to drop all tables.
            connection.execute('DROP TABLE IF EXISTS payment      CASCADE;')
            connection.execute('DROP TABLE IF EXISTS oauth_grant  CASCADE;')
            connection.execute('DROP TABLE IF EXISTS oauth_token  CASCADE;')
            connection.execute('DROP TABLE IF EXISTS oauth_client CASCADE;')
            connection.execute('DROP TABLE IF EXISTS access_log   CASCADE;')
            connection.execute('DROP TABLE IF EXISTS token_log    CASCADE;')
            connection.execute('DROP TABLE IF EXISTS token        CASCADE;')
            connection.execute('DROP TABLE IF EXISTS "user"       CASCADE;')
            connection.execute('DROP TABLE IF EXISTS tier         CASCADE;')

    def drop_types(self):
        with db.engine.connect() as connection:
            connection.execute('DROP TYPE IF EXISTS payment_method_types CASCADE;')
            connection.execute('DROP TYPE IF EXISTS state_types CASCADE;')
            connection.execute('DROP TYPE IF EXISTS token_log_action_types CASCADE;')
