from flask_testing import TestCase
from metabrainz import create_app


class FlaskTestCase(TestCase):

    def create_app(self):
        app = create_app()
        app.config['TESTING'] = True
        return app
