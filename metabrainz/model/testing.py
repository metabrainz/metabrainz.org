from flask_testing import TestCase
from metabrainz.model import db
from metabrainz import create_app


class ModelTestCase(TestCase):

    def create_app(self):
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config['TEST_SQLALCHEMY_DATABASE_URI']
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
