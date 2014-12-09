from metabrainz.testing import FlaskTestCase


class DonationsWePayViewsTestCase(FlaskTestCase):

    def test_wepay(self):
        self.assert200(self.client.get("/donations/wepay"))
