from metabrainz.testing import FlaskTestCase


class IndexViewsTestCase(FlaskTestCase):

    def test_homepage(self):
        response = self.client.get("/")
        self.assert200(response)

    def test_about(self):
        response = self.client.get("/about")
        self.assert200(response)

    def test_sponsors(self):
        response = self.client.get("/sponsors")
        self.assert200(response)

    def test_privacy_policy(self):
        response = self.client.get("/privacy")
        self.assert200(response)
