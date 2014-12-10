from metabrainz.testing import FlaskTestCase


class FinancialReportsViewsTestCase(FlaskTestCase):

    def test_index(self):
        response = self.client.get("/finances/")
        self.assert200(response)
