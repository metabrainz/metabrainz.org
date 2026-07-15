import json

from flask import url_for

from metabrainz.admin.views import OAuth2ClientModelView, PrivilegeBitmapField
from metabrainz.model import OAuth2Client, db
from metabrainz.model.oauth.client import OAuth2ClientPrivilege
from metabrainz.oauth.tests import OAuthTestCase


class OAuthPrivilegesTestCase(OAuthTestCase):

    def _get_client(self, application):
        return db.session.query(OAuth2Client).filter_by(client_id=application["client_id"]).first()

    def test_has_privilege_and_labels(self):
        application = self.create_oauth_app()
        client = self._get_client(application)

        # no privileges by default
        self.assertEqual(client.privileges, 0)
        self.assertFalse(client.has_privilege(OAuth2ClientPrivilege.REMEMBER_ME))
        self.assertEqual(client.privilege_labels(), [])

        self.grant_privileges(
            application,
            OAuth2ClientPrivilege.REMEMBER_ME,
            OAuth2ClientPrivilege.REGISTRATION_REQUEST,
        )
        client = self._get_client(application)

        self.assertTrue(client.has_privilege(OAuth2ClientPrivilege.REMEMBER_ME))
        self.assertTrue(client.has_privilege(OAuth2ClientPrivilege.REGISTRATION_REQUEST))
        self.assertFalse(client.has_privilege(OAuth2ClientPrivilege.CLIENT_CREDENTIALS))
        self.assertCountEqual(
            client.privilege_labels(),
            ["Remember me", "Registration requests"],
        )

    def test_privilege_bitmap_field_roundtrip(self):
        application = self.create_oauth_app()
        client = self._get_client(application)
        form_class = OAuth2ClientModelView(db.session).get_form()

        # bitmap -> selected checkbox values
        bitmap = OAuth2ClientPrivilege.REMEMBER_ME | OAuth2ClientPrivilege.CLIENT_CREDENTIALS
        client.privileges = int(bitmap)
        form = form_class(meta={"csrf": False}, obj=client)
        field = form.privileges
        self.assertIsInstance(field, PrivilegeBitmapField)
        self.assertCountEqual(field.data, [
            OAuth2ClientPrivilege.REMEMBER_ME.value,
            OAuth2ClientPrivilege.CLIENT_CREDENTIALS.value,
        ])

        # selected checkbox values -> bitmap written back on the OAuth client
        field.data = [
            OAuth2ClientPrivilege.CLIENT_CREDENTIALS.value,
            OAuth2ClientPrivilege.REGISTRATION_REQUEST.value,
        ]
        form.populate_obj(client)
        self.assertEqual(
            client.privileges,
            OAuth2ClientPrivilege.CLIENT_CREDENTIALS | OAuth2ClientPrivilege.REGISTRATION_REQUEST,
        )

        # empty selection clears the bitmap
        form = form_class(meta={"csrf": False}, obj=client)
        form.privileges.data = []
        form.populate_obj(client)
        self.assertEqual(client.privileges, 0)

    def test_admin_privilege_form_saves(self):
        application = self.create_oauth_app()
        client = self._get_client(application)

        self.app.config["ADMINS"] = [self.user1.name]
        self.temporary_login(self.user1)
        url = url_for("oauth-clients-admin.edit_view", id=client.id)
        response = self.client.get(url)
        self.assert200(response)
        form = self.get_context_variable("form")

        response = self.client.post(url, data={
            "csrf_token": form.csrf_token.current_token,
            "privileges": [
                str(OAuth2ClientPrivilege.REMEMBER_ME.value),
                str(OAuth2ClientPrivilege.CLIENT_CREDENTIALS.value),
                str(OAuth2ClientPrivilege.REGISTRATION_REQUEST.value),
            ],
        })

        self.assertStatus(response, 302)
        db.session.refresh(client)
        self.assertEqual(client.privileges, 7)

    def test_privileges_non_negative_constraint(self):
        from sqlalchemy.exc import IntegrityError

        application = self.create_oauth_app()
        client = self._get_client(application)
        client.privileges = -1
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_profile_applications_expose_privileges(self):
        application = self.create_oauth_app()

        self.temporary_login(self.user1)
        self.client.get("/profile/applications")
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(props["applications"][0]["privileges"], [])

        self.grant_privileges(application, OAuth2ClientPrivilege.CLIENT_CREDENTIALS)

        self.client.get("/profile/applications")
        props = json.loads(self.get_context_variable("props"))
        self.assertEqual(
            props["applications"][0]["privileges"],
            ["Client credentials grant"],
        )
