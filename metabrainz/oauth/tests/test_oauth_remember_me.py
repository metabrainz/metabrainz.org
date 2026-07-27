from datetime import datetime, timezone, timedelta

from metabrainz.model import db
from metabrainz.model.oauth.client import OAuth2ClientPrivilege
from metabrainz.oauth.tests import OAuthTestCase


class RememberMeTokenTestCase(OAuthTestCase):

    def _get_token(self, application, redirect_uri="https://example.com/callback"):
        self.temporary_login(self.user2)
        code = self.authorize_success_for_token_grant_helper(application, redirect_uri, True)
        response = self.client.post("/oauth2/token", data={
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        })
        self.assert200(response)
        return response.json

    def test_remember_me_true_for_whitelisted_client(self):
        application = self.create_oauth_app(privileges=[OAuth2ClientPrivilege.REMEMBER_ME])

        self.user2.update_remember_me(True)
        db.session.commit()

        data = self._get_token(application)
        self.assertIn("remember_me", data)
        self.assertTrue(data["remember_me"])

    def test_remember_me_false_for_whitelisted_client(self):
        application = self.create_oauth_app(privileges=[OAuth2ClientPrivilege.REMEMBER_ME])

        self.user2.update_remember_me(False)
        db.session.commit()

        data = self._get_token(application)
        self.assertIn("remember_me", data)
        self.assertFalse(data["remember_me"])

    def test_remember_me_false_when_expired(self):
        application = self.create_oauth_app(privileges=[OAuth2ClientPrivilege.REMEMBER_ME])

        # remember-me cookie that has already expired should report False
        self.user2.remember_me_until = datetime.now(timezone.utc) - timedelta(days=1)
        db.session.commit()

        data = self._get_token(application)
        self.assertIn("remember_me", data)
        self.assertFalse(data["remember_me"])

    def test_remember_me_absent_for_non_whitelisted_client(self):
        application = self.create_oauth_app()

        self.user2.update_remember_me(True)
        db.session.commit()

        data = self._get_token(application)
        self.assertNotIn("remember_me", data)

    def test_remember_me_present_on_refresh_token_grant(self):
        application = self.create_oauth_app(privileges=[OAuth2ClientPrivilege.REMEMBER_ME])

        self.user2.update_remember_me(True)
        db.session.commit()

        token = self._get_token(application)

        response = self.client.post("/oauth2/token", data={
            "client_id": application["client_id"],
            "client_secret": application["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        })
        self.assert200(response)
        self.assertIn("remember_me", response.json)
        self.assertTrue(response.json["remember_me"])
