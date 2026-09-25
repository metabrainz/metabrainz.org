from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import select
from flask import g, url_for
from brainzutils import cache
from click.testing import CliRunner

from metabrainz.crm.client import CrmError
from metabrainz.crm.cli import crm_sync
from metabrainz.crm.tasks import prepare_signup_sync, publish_signup_sync, requeue_pending_supporters, sync_supporter_to_crm
from metabrainz.model import db, Supporter
from metabrainz.model.crm_sync import CrmSync
from metabrainz.model.user import User
from metabrainz.model.tier import Tier
from metabrainz.supporter.views import _commit_supporter_signup
from metabrainz.testing import FlaskTestCase


class CrmTasksTestCase(FlaskTestCase):
    def setUp(self):
        super().setUp()
        self.app.config["CRM_ENABLED"] = True
        self.user = User(name="crm-user", password="unused")
        self.supporter = Supporter.add(
            user=self.user, is_commercial=False, contact_name="Contact", data_usage_desc="Research",
        )

    def tearDown(self):
        self.app.config["CRM_ENABLED"] = False
        cache._r.flushall()
        super().tearDown()

    def _signup(self, commercial, existing):
        db.session.rollback()
        tier = Tier.create(name="CRM test", price=100, available=True)
        if existing:
            user = User(name="existing-crm", password="unused")
            db.session.add(user)
            db.session.commit()
            self.temporary_login(user)
        url = url_for("supporters.signup_commercial", tier_id=tier.id) if commercial else url_for(
            "supporters.signup_noncommercial"
        )
        self.client.get(url)
        data = {
            "username": "new-crm", "email": "new-crm@example.com",
            "password": "securepassword123", "confirm_password": "securepassword123",
            "contact_name": "CRM Contact", "usage_desc": "Research project",
            "agreement": "y", "mtcaptcha": "test-token", "csrf_token": g.csrf_token,
        }
        if commercial:
            data.update(org_name="CRM Company", org_desc="Description", website_url="https://example.com",
                        address_street="Street", address_city="City", address_state="State",
                        address_postcode="12345", address_country="Country", amount_pledged="100")
        with patch("metabrainz.crm.tasks.sync_supporter_to_crm.apply_async", side_effect=RuntimeError("broker down")) as publish:
            response = self.client.post(url, data=data)
        self.assertRedirects(response, url_for("index.profile"))
        supporter = Supporter.query.one()
        self.assertEqual(supporter.is_commercial, commercial)
        self.assertTrue(db.session.get(CrmSync, supporter.id).pending)
        publish.assert_called_once_with(args=[supporter.id], retry=False)

    def test_new_commercial_signup_survives_broker_failure(self):
        self._signup(True, False)

    def test_existing_commercial_signup_survives_broker_failure(self):
        self._signup(True, True)

    def test_new_noncommercial_signup_survives_broker_failure(self):
        self._signup(False, False)

    def test_existing_noncommercial_signup_survives_broker_failure(self):
        self._signup(False, True)

    def test_rollback_does_not_leave_pending_work(self):
        prepare_signup_sync(self.supporter)
        db.session.flush()
        db.session.rollback()
        self.assertEqual(CrmSync.query.count(), 0)
        self.assertEqual(Supporter.query.count(), 0)

    @patch("metabrainz.crm.tasks.sync_supporter_to_crm.apply_async")
    def test_publish_sees_committed_signup(self, publish):
        def check_committed(**kwargs):
            # A separate connection cannot see an uncommitted pending row.
            with db.engine.connect() as connection:
                self.assertIsNotNone(connection.execute(
                    select(CrmSync.supporter_id).where(CrmSync.supporter_id == kwargs["args"][0])
                ).first())
        publish.side_effect = check_committed
        _commit_supporter_signup(self.supporter)
        publish.assert_called_once_with(args=[self.supporter.id], retry=False)

    @patch("metabrainz.crm.tasks.sync_supporter_to_crm.apply_async", side_effect=RuntimeError("broker down"))
    def test_broker_failure_keeps_signup_and_recovery_work(self, publish):
        _commit_supporter_signup(self.supporter)
        self.assertEqual(Supporter.query.count(), 1)
        self.assertTrue(db.session.get(CrmSync, self.supporter.id).pending)
        publish.side_effect = None
        requeue_pending_supporters.run()
        self.assertEqual(publish.call_count, 2)
        # Recovery scans are throttled even when publishing fails repeatedly.
        requeue_pending_supporters.run()
        self.assertEqual(publish.call_count, 2)

    @patch("metabrainz.crm.tasks.TwentyClient")
    @patch("metabrainz.crm.tasks.sync_supporter")
    def test_task_success_and_duplicate_delivery(self, sync, client):
        prepare_signup_sync(self.supporter)
        db.session.commit()
        sync.return_value = (str(uuid4()), None)
        sync_supporter_to_crm.run(self.supporter.id)
        mapping = db.session.get(CrmSync, self.supporter.id)
        self.assertFalse(mapping.pending)
        self.assertIsNotNone(mapping.synced_at)
        sync_supporter_to_crm.run(self.supporter.id)
        sync.assert_called_once()

    @patch("metabrainz.crm.tasks.TwentyClient")
    @patch("metabrainz.crm.tasks.sync_supporter", side_effect=CrmError("Twenty returned HTTP 503"))
    def test_http_failure_is_recoverable(self, sync, client):
        prepare_signup_sync(self.supporter)
        db.session.commit()
        sync_supporter_to_crm.run(self.supporter.id)
        mapping = db.session.get(CrmSync, self.supporter.id)
        self.assertTrue(mapping.pending)
        self.assertEqual(mapping.attempts, 1)
        self.assertIn("503", mapping.last_error)
        self.assertGreater(mapping.next_attempt_at, datetime.now(timezone.utc))

    @patch("metabrainz.crm.tasks.TwentyClient")
    def test_parallel_delivery_skips_locked_supporter(self, client):
        prepare_signup_sync(self.supporter)
        db.session.commit()
        with db.engine.connect() as connection, connection.begin():
            connection.execute(select(CrmSync).where(
                CrmSync.supporter_id == self.supporter.id
            ).with_for_update())
            sync_supporter_to_crm.run(self.supporter.id)
        client.assert_not_called()
        self.assertTrue(db.session.get(CrmSync, self.supporter.id).pending)

    @patch("metabrainz.crm.tasks.sync_supporter_to_crm.apply_async")
    def test_disabled_integration_does_not_enqueue(self, publish):
        self.app.config["CRM_ENABLED"] = False
        _commit_supporter_signup(self.supporter)
        requeue_pending_supporters.run()
        publish_signup_sync(self.supporter.id)
        publish.assert_not_called()
        self.assertEqual(CrmSync.query.count(), 0)

    @patch("metabrainz.crm.cli.create_app")
    @patch("metabrainz.crm.tasks.sync_supporter_to_crm.apply_async")
    def test_cli_records_explicit_mapping_and_schedules_work(self, publish, create_app):
        db.session.commit()
        create_app.return_value = self.app
        company_id = uuid4()
        supporter_id = self.supporter.id
        result = CliRunner().invoke(crm_sync, [str(supporter_id), "--company-id", str(company_id)])
        self.assertEqual(result.exit_code, 0, result.output)
        mapping = db.session.get(CrmSync, supporter_id)
        self.assertEqual(mapping.company_id, company_id)
        self.assertTrue(mapping.pending)
        publish.assert_called_once_with(args=[supporter_id], retry=False)
