import unittest

from flask import template_rendered, message_flashed

from metabrainz import create_app as create_web_app
from metabrainz import model
from metabrainz import db
import logging
import os.path
import os

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'admin', 'sql')


class FlaskTestCase(unittest.TestCase):
    """ TestCase for Flask App tests, most of the code here has been borrowed from flask_testing.TestCase
    (https://github.com/jarus/flask-testing/blob/5107691011fa891835c01547e73e991c484fa07f/flask_testing/utils.py#L118).
    A key difference is that flask_testing's TestCase creates the flask app for each test method whereas
    our FlaskTestCase creates it once per class. flask_testing's test case allows also for custom Response mixins
    and other stuff to be compatible across flask versions. Since, we don't need that the implementation can be
    simplified.

    Notably, the implementation of the setUpClass, setUp, tearDown, tearDownClass, assertMessageFlashed,
    assertTemplateUsed has been adapted to use class level variables. The implementation of assertRedirects has been
    modified to fix concerning absolute and relative urls in Location header.
    """

    @classmethod
    def create_app(cls):
        app = create_web_app(config_path=os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            '..', 'config.py'
        ))
        app.config['TESTING'] = True
        db.init_db_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        return app

    def temporary_login(self, user_login_id):
        with self.client.session_transaction() as session:
            session['_user_id'] = user_login_id
            session['_fresh'] = True

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.DEBUG)

        cls.app = cls.create_app()
        cls.client = cls.app.test_client()

        template_rendered.connect(cls._set_template)
        message_flashed.connect(cls._add_flash_message)

        cls.template = None
        cls.flashed_messages = []

    def setUp(self):
        self._ctx = self.app.test_request_context()
        self._ctx.push()
        self.reset_db()

        FlaskTestCase.template = None
        FlaskTestCase.flashed_messages = []

    @classmethod
    def _add_flash_message(cls, app, message, category):
        cls.flashed_messages.append((message, category))

    @classmethod
    def _set_template(cls, app, template, context):
        cls.template = (template, context)

    def tearDown(self):
        model.db.session.remove()
        self._ctx.pop()
        del self._ctx
        del FlaskTestCase.template
        del FlaskTestCase.flashed_messages

    @classmethod
    def tearDownClass(cls):
        template_rendered.disconnect(cls._set_template)
        message_flashed.disconnect(cls._add_flash_message)
        del cls.client
        del cls.app

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

    def assertMessageFlashed(self, message, category='message'):
        """
        Checks if a given message was flashed.
        Only works if your version of Flask has message_flashed
        signal support (0.10+) and blinker is installed.
        :param message: expected message
        :param category: expected message category
        """
        for _message, _category in FlaskTestCase.flashed_messages:
            if _message == message and _category == category:
                return True

        raise AssertionError("Message '%s' in category '%s' wasn't flashed" % (message, category))

    def assertTemplateUsed(self, name):
        """
        Checks if a given template is used in the request.
        Only works if your version of Flask has signals
        support (0.6+) and blinker is installed.
        If the template engine used is not Jinja2, provide
        ``tmpl_name_attribute`` with a value of its `Template`
        class attribute name which contains the provided ``name`` value.
        :versionadded: 0.2
        :param name: template name
        """
        used_template = FlaskTestCase.template[0].name
        self.assertEqual(used_template, name, f"Template {name} not used. Template used: {used_template}")

    def get_context_variable(self, name):
        context = FlaskTestCase.template[1]
        if name in context:
            return context[name]
        raise ValueError()

    def assertContext(self, name, value, message=None):
        try:
            self.assertEqual(self.get_context_variable(name), value, message)
        except ValueError:
            self.fail(message or "Context variable does not exist: %s" % name)

    assert_context = assertContext

    def assertRedirects(self, response, location, message=None, permanent=False):
        if permanent:
            valid_status_codes = (301, 308)
        else:
            valid_status_codes = (301, 302, 303, 305, 307, 308)

        valid_status_code_str = ', '.join(str(code) for code in valid_status_codes)
        not_redirect = "HTTP Status %s expected but got %d" % (valid_status_code_str, response.status_code)

        self.assertIn(response.status_code, valid_status_codes, message or not_redirect)
        location_mismatch = "Expected redirect location %s but got %s" % (response.location, location)
        self.assertTrue(response.location.endswith(location), message or location_mismatch)

    def assertStatus(self, response, status_code, message=None):
        message = message or 'HTTP Status %s expected but got %s' \
                             % (status_code, response.status_code)
        self.assertEqual(response.status_code, status_code, message)

    def assert200(self, response, message=None):
        self.assertStatus(response, 200, message)

    def assert400(self, response, message=None):
        self.assertStatus(response, 400, message)

    def assert401(self, response, message=None):
        self.assertStatus(response, 401, message)

    def assert403(self, response, message=None):
        self.assertStatus(response, 403, message)

    def assert404(self, response, message=None):
        self.assertStatus(response, 404, message)

    def assert500(self, response, message=None):
        self.assertStatus(response, 500, message)
    
    def assert503(self, response, message=None):
        self.assertStatus(response, 503, message)