from metabrainz.model.user import User
from metabrainz.testing import FlaskTestCase
from metabrainz.model import AccessLog, Supporter
from metabrainz.model.supporter import STATE_ACTIVE


class AccessLogTestCase(FlaskTestCase):

    def setUp(self):
        super(AccessLogTestCase, self).setUp()

    def test_access_log(self):
        user_0 = User.add(name="mb_test", unconfirmed_email="test@musicbrainz.org", password="<PASSWORD>")
        supporter_0 = Supporter.add(is_commercial=False, contact_name="Mr. Test", data_usage_desc="poop!",
                                    org_desc="foo!", user=user_0)
        supporter_0.set_state(STATE_ACTIVE)
        token_0 = supporter_0.generate_token()
        AccessLog.create_record(token_0, "10.1.1.69")
        AccessLog.create_record(token_0, "10.1.1.69")

        user_1 = User.add(name="mb_commercial", unconfirmed_email="testc@musicbrainz.org", password="<PASSWORD>")
        supporter_1 = Supporter.add(is_commercial=True, contact_name="Mr. Commercial", data_usage_desc="poop!",
                                    org_desc="foo!", user=user_1)
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
