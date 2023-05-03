from urllib.parse import urlparse
from flask import url_for
from metabrainz import create_app
from metabrainz.testing import FlaskTestCase


class IndexViewsTestCase(FlaskTestCase):

    def test_homepage(self):
        response = self.client.get(url_for('index.home'))
        self.assert200(response)

    def test_contact(self):
        response = self.client.get(url_for('index.contact'))
        self.assert200(response)

    def test_code_of_conduct(self):
        response = self.client.get(url_for('index.code_of_conduct'))
        self.assert200(response)

    def test_socialcontract(self):
        response = self.client.get(url_for('index.social_contract'))
        self.assert200(response)

    def test_about(self):
        response = self.client.get(url_for('index.about'))
        self.assert200(response)

    def test_projects(self):
        response = self.client.get(url_for('index.projects'))
        self.assert200(response)

    def test_team(self):
        response = self.client.get(url_for('index.team'))
        self.assert200(response)

    def test_sponsors(self):
        response = self.client.get(url_for('index.sponsors'))
        self.assert200(response)

    def test_bad_customers(self):
        response = self.client.get(url_for('index.bad_customers'))
        self.assert200(response)

    def test_privacy_policy(self):
        response = self.client.get(url_for('index.privacy_policy'))
        self.assert200(response)

    def test_about_customers(self):
        resp = self.client.get(url_for('index.about_customers_redirect'))

        # Changed to assertEqual since assertRedirect kept doing stupid shit
        self.assertEqual(resp.location, urlparse(url_for('users.supporters_list')).path)

    def test_flask_debugtoolbar(self):
        """ Test if flask debugtoolbar is loaded correctly

        Creating an app with default config so that debug is True
        and SECRET_KEY is defined.
        """
        app = create_app(debug=True, config_path='../config.py')
        app.config['TESTING'] = True
        client = app.test_client()
        resp = client.get('/about')
        self.assert200(resp)
        self.assertIn('flDebug', str(resp.data))

    def test_shop(self):
        response = self.client.get(url_for('index.shop'))
        self.assert200(response)

    def test_datasets(self):
        response = self.client.get(url_for('index.datasets'))
        self.assert200(response)

    def test_postgres_dumps(self):
        response = self.client.get(url_for('index.postgres_dumps'))
        self.assert200(response)

    def test_derived_dumps(self):
        response = self.client.get(url_for('index.derived_dumps'))
        self.assert200(response)

    def test_dataset_signup(self):
        response = self.client.get(url_for('index.signup'))
        self.assert200(response)

    def test_dataset_download(self):
        response = self.client.get(url_for('index.download'))
        self.assert200(response)
