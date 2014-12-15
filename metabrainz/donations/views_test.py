from metabrainz.testing import FlaskTestCase


class DonationsViewsTestCase(FlaskTestCase):

    def test_index(self):
        self.assert200(self.client.get("/donations/"))

    def test_donors(self):
        response = self.client.get("/donations/donors")
        self.assert200(response)

    def test_complete(self):
        self.assert200(self.client.get("/donations/complete"))
        self.assert200(self.client.post("/donations/complete"))

    def test_cancelled(self):
        self.assert200(self.client.get("/donations/cancelled"))

    def test_error(self):
        self.assert200(self.client.get("/donations/error"))
