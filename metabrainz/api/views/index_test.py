from metabrainz.testing import FlaskTestCase


class IndexViewsTestCase(FlaskTestCase):

    def test_info(self):
        self.assert200(self.client.get("/api/"))
