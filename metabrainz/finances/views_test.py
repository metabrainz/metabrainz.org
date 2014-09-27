from metabrainz.testing import FlaskTestCase


class FinancesViewsTestCase(FlaskTestCase):

    def test_index(self):
        response = self.client.get("/finances/")
        self.assert200(response)

    def test_donations(self):
        response = self.client.get("/finances/donations")
        self.assert200(response)

    def test_highest_donors(self):
        response = self.client.get("/finances/donations/by-amount")
        self.assert200(response)

    def test_historical(self):
        response = self.client.get("/finances/historical")
        self.assert200(response)
