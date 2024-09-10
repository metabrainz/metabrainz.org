from metabrainz.testing import FlaskTestCase
from metabrainz.model import AccessLog, db, Supporter
from metabrainz.model.supporter import STATE_ACTIVE
from flask import current_app
import copy


class AccessLogTestCase(FlaskTestCase):

    def setUp(self):
        super(AccessLogTestCase, self).setUp()

    def test_access_log(self):
        supporter_0 = Supporter.add(is_commercial=False,
                                    musicbrainz_id="mb_test",
                                    musicbrainz_row_id=1,
                                    contact_name="Mr. Test",
                                    contact_email="test@musicbrainz.org",
                                    data_usage_desc="poop!",
                                    org_desc="foo!",
                                    )
        supporter_0.set_state(STATE_ACTIVE)
        token_0 = supporter_0.generate_token()
        AccessLog.create_record(token_0, "10.1.1.69")
        AccessLog.create_record(token_0, "10.1.1.69")

        supporter_1 = Supporter.add(is_commercial=True,
                                    musicbrainz_id="mb_commercial",
                                    musicbrainz_row_id=3,
                                    contact_name="Mr. Commercial",
                                    contact_email="testc@musicbrainz.org",
                                    data_usage_desc="poop!",
                                    org_desc="foo!"
                                    )
        supporter_1.set_state(STATE_ACTIVE)
        token_1 = supporter_1.generate_token()
        AccessLog.create_record(token_1, "10.1.1.59")

        non_commercial, commercial = AccessLog.top_ips()

        # Check that we have the right number of rows
        self.assertEqual(len(non_commercial), 1)
        self.assertEqual(len(commercial), 1)
        self.assertEqual(non_commercial[0][0], "10.1.1.69")
        self.assertEqual(commercial[0][0], "10.1.1.59")

        # Check that we have the right number of counts
        self.assertEqual(non_commercial[0][7], 2)
        self.assertEqual(commercial[0][7], 1)

        non_commercial, commercial = AccessLog.top_tokens()

        # Check that we have the right number of rows
        self.assertEqual(len(non_commercial), 1)
        self.assertEqual(len(commercial), 1)
        self.assertEqual(non_commercial[0][0], token_0)
        self.assertEqual(commercial[0][0], token_1)

        # Check that we have the right number of counts
        self.assertEqual(non_commercial[0][5], 2)
        self.assertEqual(commercial[0][5], 1)
