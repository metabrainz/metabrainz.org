from metabrainz.testing import FlaskTestCase


class IndexViewsTestCase(FlaskTestCase):

    def test_home(self):
        response = self.client.get("/")
        self.assert200(response)

    def test_customers(self):
        response = self.client.get("/customers")
        self.assert200(response)

    def test_sponsors(self):
        response = self.client.get("/sponsors")
        self.assert200(response)

    def test_white_papers(self):
        response = self.client.get("/white-papers")
        self.assert200(response)

    def test_privacy_policy(self):
        response = self.client.get("/privacy")
        self.assert200(response)

    def test_contact(self):
        response = self.client.get("/contact")
        self.assert200(response)

    def test_404(self):
        response = self.client.get("/404")
        self.assert404(response)
