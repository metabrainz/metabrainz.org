from metabrainz.testing import FlaskTestCase


class DonationViewsTestCase(FlaskTestCase):

    def test_index(self):
        self.assert200(self.client.get("/donate/"))

    def test_paypal(self):
        self.assert200(self.client.get("/donate/paypal"))

    def test_wepay(self):
        self.assert200(self.client.get("/donate/wepay"))

    def test_complete(self):
        self.assert200(self.client.get("/donate/complete"))
        self.assert200(self.client.post("/donate/complete"))

    def test_cancelled(self):
        self.assert200(self.client.get("/donate/cancelled"))

    def test_error(self):
        self.assert200(self.client.get("/donate/error"))
