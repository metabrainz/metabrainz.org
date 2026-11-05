from metabrainz.model import db
from metabrainz.model.supporter import (
    InactiveSupporterException,
    STATE_ACTIVE,
    STATE_CANCELLED,
    STATE_CLOSED,
    STATE_LIMITED,
    STATE_PENDING,
    STATE_PRE_REVENUE,
    STATE_REJECTED,
    STATE_WAITING,
    Supporter,
)
from metabrainz.model.token import Token
from metabrainz.model.user import User
from metabrainz.testing import FlaskTestCase


class SupporterStatesTestCase(FlaskTestCase):

    def _create_supporter(self, name="supporter_user", **kwargs):
        user = User.add(name=name, unconfirmed_email=f"{name}@example.com", password="password123")
        supporter = Supporter.add(
            is_commercial=False,
            contact_name="Test Supporter",
            data_usage_desc="Test usage",
            user=user,
        )
        db.session.commit()
        if kwargs:
            supporter.update(**kwargs)
        return supporter

    def test_token_is_only_valid_while_owner_is_active(self):
        supporter = self._create_supporter()
        token = supporter.generate_token()
        self.assertTrue(Token.is_valid(token))

        for state in (STATE_PRE_REVENUE, STATE_PENDING, STATE_WAITING, STATE_REJECTED,
                      STATE_LIMITED, STATE_CANCELLED, STATE_CLOSED):
            with self.subTest(state=state):
                supporter.update(state=state)
                self.assertFalse(Token.is_valid(token))

        # the token itself was not revoked, so restoring the supporter restores access
        supporter.update(state=STATE_ACTIVE)
        self.assertTrue(Token.is_valid(token))

    def test_token_without_owner_stays_valid(self):
        self.assertTrue(Token.is_valid(Token.generate_token(owner_id=None)))

    def test_former_supporters_cannot_generate_tokens(self):
        supporter = self._create_supporter()
        for state in (STATE_CANCELLED, STATE_CLOSED):
            with self.subTest(state=state):
                supporter.update(state=state)
                with self.assertRaises(InactiveSupporterException):
                    supporter.generate_token()

    def test_get_featured_excludes_former_supporters(self):
        active = self._create_supporter("active_user", featured=True)
        self._create_supporter("cancelled_user", featured=True, state=STATE_CANCELLED)
        self._create_supporter("closed_user", featured=True, state=STATE_CLOSED)
        self.assertEqual([s.id for s in Supporter.get_featured()], [active.id])

    def test_get_featured_excludes_former_supporters_in_deadbeat_club(self):
        self._create_supporter("closed_user", featured=True, state=STATE_CLOSED, in_deadbeat_club=True)
        self.assertEqual(Supporter.get_featured(in_deadbeat_club=True), [])
