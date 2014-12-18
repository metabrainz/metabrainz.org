from metabrainz.testing import FlaskTestCase
from flask import url_for


class FinancialReportsViewsTestCase(FlaskTestCase):

    def test_index(self):
        response = self.client.get(url_for('financial_reports.index'))
        self.assert200(response)
