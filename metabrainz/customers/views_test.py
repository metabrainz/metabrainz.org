from metabrainz.testing import FlaskTestCase


class CustomersViewsTestCase(FlaskTestCase):

    def test_index(self):
        self.assert200(self.client.get("/customers/"))

    def test_tiers(self):
        self.assert200(self.client.get("/customers/tiers/"))

    def test_bad(self):
        self.assert200(self.client.get("/customers/bad"))
