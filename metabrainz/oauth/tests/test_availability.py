from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from brainzutils import cache

from metabrainz.model import db, OAuth2AccessToken, OAuth2Client
from metabrainz.oauth.tests import OAuthTestCase


class AvailabilityOAuthTestCase(OAuthTestCase):
    def tearDown(self):
        cache._r.flushall()
        super().tearDown()

    def token(self, client_id, value, **kwargs):
        token = OAuth2AccessToken(
            client_id=client_id, access_token=value, expires_in=3600,
            issued_at=datetime.now(timezone.utc), **kwargs,
        )
        db.session.add(token)
        db.session.commit()
        return token

    def check(self, field, token=None):
        return self.client.post(
            f"/check-{field}",
            json={field: "available" if field == "username" else "available@example.com"},
            headers={"Authorization": f"Bearer {token}"} if token else {},
        )

    def test_valid_tokens_share_higher_client_allowance(self):
        application = self.create_oauth_app()
        client = db.session.query(OAuth2Client).filter_by(client_id=application["client_id"]).one()
        self.token(client.id, "first")
        self.token(client.id, "second", user_id=self.user1.id)
        with patch.dict(self.app.config, AVAILABILITY_RATE_LIMIT_PER_IP=1,
                        AVAILABILITY_RATE_LIMIT_PER_CLIENT=3):
            self.assertEqual(self.check("email").status_code, 200)
            self.assertEqual(self.check("username").status_code, 429)
            self.assertEqual(self.check("email", "first").status_code, 200)
            self.assertEqual(self.check("username", "second").status_code, 200)
            self.assertEqual(self.check("email", "second").status_code, 200)
            self.assertEqual(self.check("username", "first").status_code, 429)

    def test_invalid_tokens_do_not_get_relaxed_limits(self):
        application = self.create_oauth_app()
        client = db.session.query(OAuth2Client).filter_by(client_id=application["client_id"]).one()
        self.token(client.id, "revoked", revoked=True)
        expired = self.token(client.id, "expired")
        expired.issued_at = datetime.now(timezone.utc) - timedelta(hours=2)
        db.session.commit()
        for field in ("email", "username"):
            for token in ("unknown", "revoked", "expired", "malformed token"):
                with self.subTest(field=field, token=token):
                    response = self.check(field, token)
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.json, {"error": "invalid_token"})
                    self.assertIn("Bearer", response.headers["WWW-Authenticate"])
