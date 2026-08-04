from sqlalchemy import delete

from metabrainz.model import db
from metabrainz.model.user import User
from metabrainz.testing import FlaskTestCase
from metabrainz.user import load_user


class LoadUserTestCase(FlaskTestCase):

    def setUp(self):
        super(LoadUserTestCase, self).setUp()
        self.user = User.add(
            name="test_user_1",
            password="<PASSWORD>",
            unconfirmed_email="test@example.com",
        )
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        db.session.execute(delete(User))
        db.session.commit()
        super(LoadUserTestCase, self).tearDown()

    def test_loads_user_by_login_id(self):
        loaded = load_user(str(self.user.login_id))
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.id, self.user.id)

    def test_legacy_integer_session_id_returns_none(self):
        """ Sessions predating the switch from the integer primary key to login_id carry an
        integer, which postgres cannot cast to uuid. """
        self.assertIsNone(load_user(str(self.user.id)))
        self.assertIsNone(load_user("560"))

    def test_malformed_login_id_returns_none(self):
        self.assertIsNone(load_user("garbage"))
        self.assertIsNone(load_user(""))
        self.assertIsNone(load_user(None))

    def test_unknown_login_id_returns_none(self):
        self.assertIsNone(load_user("00000000-0000-4000-8000-000000000000"))
