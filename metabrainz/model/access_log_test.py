from metabrainz.testing import FlaskTestCase
from metabrainz.model import AccessLog, db, User
from metabrainz.model.user import STATE_ACTIVE
from flask import current_app
import copy


class AccessLogTestCase(FlaskTestCase):

    def setUp(self):
        super(AccessLogTestCase, self).setUp()

    def test_access_log(self):

        user = User.add(is_commercial=False, 
            musicbrainz_id = "mb_test", 
            contact_name = "Mr. Test",
            contact_email = "test@musicbrainz.org",
            data_usage_desc = "poop!",
            org_desc = "foo!",
        )
        user.set_state(STATE_ACTIVE)
        token = user.generate_token() 
        AccessLog.create_record(token, "10.1.1.69")
        AccessLog.create_record(token, "10.1.1.69")

        user = User.add(is_commercial=True, 
            musicbrainz_id = "mb_commercial", 
            contact_name = "Mr. Commercial",
            contact_email = "testc@musicbrainz.org",
            data_usage_desc = "poop!",
            org_desc = "foo!"
        )
        user.set_state(STATE_ACTIVE)
        token = user.generate_token() 
        AccessLog.create_record(token, "10.1.1.59")

        non_commercial, commercial = AccessLog.top_ips()

        # Check that we have the right number of rows
        self.assertEqual(len(non_commercial), 1)
        self.assertEqual(len(commercial), 1)
        self.assertEqual(non_commercial[0][0], "10.1.1.69")
        self.assertEqual(commercial[0][0], "10.1.1.59")

        # Check that we have the right number of counts
        self.assertEqual(non_commercial[0][6], 2)
        self.assertEqual(commercial[0][6], 1)
