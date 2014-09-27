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
