from datetime import datetime, timedelta, timezone

from metabrainz.model import (
    OAuth2AccessToken,
    OAuth2Client,
    OAuth2RefreshToken,
    db,
)
from metabrainz.oauth.tasks import cleanup_old_tokens
from metabrainz.oauth.tests import OAuthTestCase


class OAuthTasksTestCase(OAuthTestCase):

    def setUp(self):
        super().setUp()
        self.oauth_client = OAuth2Client(
            client_id="test-client-id",
            client_secret="test-client-secret",
            owner_id=self.user1.id,
            name="Test client",
            description="Test client description",
            website="https://example.com",
            redirect_uris=["https://example.com/callback"],
        )
        db.session.add(self.oauth_client)
        db.session.commit()

    def _create_access_token(self, token_value, issued_at, expires_in=3600, revoked=False):
        token = OAuth2AccessToken(
            user_id=self.user2.id,
            client_id=self.oauth_client.id,
            access_token=token_value,
            issued_at=issued_at,
            expires_in=expires_in,
            revoked=revoked,
        )
        db.session.add(token)
        return token

    def _create_refresh_token(self, token_value, issued_at, expires_in=3600, revoked=False):
        token = OAuth2RefreshToken(
            user_id=self.user2.id,
            client_id=self.oauth_client.id,
            refresh_token=token_value,
            issued_at=issued_at,
            expires_in=expires_in,
            revoked=revoked,
        )
        db.session.add(token)
        return token

    def test_cleanup_old_tokens_removes_old_expired_and_revoked_tokens(self):
        now = datetime.now(timezone.utc)

        old_expired_access = self._create_access_token(
            "old-expired-access",
            issued_at=now - timedelta(days=10),
        )
        old_revoked_access = self._create_access_token(
            "old-revoked-access",
            issued_at=now - timedelta(days=8),
            expires_in=30 * 24 * 60 * 60,
            revoked=True,
        )
        recent_revoked_access = self._create_access_token(
            "recent-revoked-access",
            issued_at=now - timedelta(days=1),
            expires_in=30 * 24 * 60 * 60,
            revoked=True,
        )
        active_access = self._create_access_token(
            "active-access",
            issued_at=now,
            expires_in=30 * 24 * 60 * 60,
        )

        old_expired_refresh = self._create_refresh_token(
            "old-expired-refresh",
            issued_at=now - timedelta(days=10),
        )
        old_revoked_refresh = self._create_refresh_token(
            "old-revoked-refresh",
            issued_at=now - timedelta(days=8),
            expires_in=30 * 24 * 60 * 60,
            revoked=True,
        )
        recent_revoked_refresh = self._create_refresh_token(
            "recent-revoked-refresh",
            issued_at=now - timedelta(days=1),
            expires_in=30 * 24 * 60 * 60,
            revoked=True,
        )
        active_refresh = self._create_refresh_token(
            "active-refresh",
            issued_at=now,
            expires_in=30 * 24 * 60 * 60,
        )

        db.session.commit()

        removed_access_ids = {old_expired_access.id, old_revoked_access.id}
        kept_access_ids = {recent_revoked_access.id, active_access.id}
        removed_refresh_ids = {old_expired_refresh.id, old_revoked_refresh.id}
        kept_refresh_ids = {recent_revoked_refresh.id, active_refresh.id}

        result = cleanup_old_tokens(days=7)

        self.assertEqual(result["access_tokens"], 2)
        self.assertEqual(result["refresh_tokens"], 2)
        self.assertEqual(result["total"], 4)

        db.session.expire_all()

        for token_id in removed_access_ids:
            self.assertIsNone(db.session.get(OAuth2AccessToken, token_id))
        for token_id in kept_access_ids:
            self.assertIsNotNone(db.session.get(OAuth2AccessToken, token_id))

        for token_id in removed_refresh_ids:
            self.assertIsNone(db.session.get(OAuth2RefreshToken, token_id))
        for token_id in kept_refresh_ids:
            self.assertIsNotNone(db.session.get(OAuth2RefreshToken, token_id))

    def test_cleanup_old_tokens_beat_schedule(self):
        schedule = self.app.extensions["celery"].conf.beat_schedule["oauth-cleanup-old-tokens"]

        self.assertEqual(schedule["task"], "metabrainz.oauth.tasks.cleanup_old_tokens")
        self.assertEqual(schedule["args"], (7,))
        self.assertEqual(schedule["options"], {"queue": "webhooks_maintenance"})
