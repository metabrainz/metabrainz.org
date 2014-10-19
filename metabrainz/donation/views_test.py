from metabrainz.testing import FlaskTestCase


class DonationViewsTestCase(FlaskTestCase):

    def test_index(self):
        response = self.client.get("/donate/")
        self.assert200(response)

    def test_paypal(self):
        response = self.client.get("/donate/paypal")
        self.assert200(response)

    def test_wepay(self):
        response = self.client.get("/donate/wepay")
        self.assert200(response)

    def test_complete(self):
        self.assert200(self.client.get("/donate/complete"))
        self.assert200(self.client.post("/donate/complete"))

    def test_cancelled(self):
        response = self.client.get("/donate/cancelled")
        self.assert200(response)

    def test_error(self):
        response = self.client.get("/donate/error")
        self.assert200(response)
