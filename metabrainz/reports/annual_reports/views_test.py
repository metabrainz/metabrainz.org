from metabrainz.testing import FlaskTestCase


class ReportsViewsTestCase(FlaskTestCase):

    def test_index(self):
        response = self.client.get("/reports/")
        self.assert200(response)
