import hashlib
import hmac
import json
import time
from unittest.mock import patch, MagicMock

from flask import url_for

from metabrainz.model import db
from metabrainz.model.payment import StripeChargeNotReadyError
from metabrainz.model.supporter import Supporter
from metabrainz.model.user import User
from metabrainz.testing import FlaskTestCase


class StripePayViewTestCase(FlaskTestCase):

    @classmethod
    def create_app(cls):
        app = super().create_app()
        app.config['WTF_CSRF_ENABLED'] = False
        return app

    def _create_supporter(self, **kwargs):
        user = User.add(
            name='test_user',
            unconfirmed_email='test@example.org',
            password='testing',
        )
        defaults = dict(
            is_commercial=True,
            contact_name='Test User',
            data_usage_desc='Testing',
            user=user,
        )
        defaults.update(kwargs)
        supporter = Supporter.add(**defaults)
        db.session.flush()
        return supporter

    @patch("stripe.checkout.Session")
    def test_one_time_payment_with_invoice_number(self, mock_session):
        self.client.post(
            url_for("payments_stripe.pay", donation=False),
            data={
                "amount": "100",
                "currency": "usd",
                "invoice_number": "42",
            },
        )

        call_kwargs = mock_session.create.call_args[1]
        metadata = call_kwargs["payment_intent_data"]["metadata"]
        self.assertEqual(metadata["invoice_number"], 42)
        self.assertIn("Invoice 42", call_kwargs["payment_intent_data"]["description"])

    @patch("stripe.checkout.Session")
    def test_one_time_payment_without_invoice_number_fails(self, mock_session):
        """One-time payment without invoice number should redirect to error."""
        resp = self.client.post(
            url_for("payments_stripe.pay", donation=False),
            data={
                "amount": "100",
                "currency": "usd",
            },
        )
        self.assertRedirects(resp, url_for("payments.error", is_donation=False))
        mock_session.create.assert_not_called()

    @patch("stripe.checkout.Session")
    def test_recurring_payment_without_invoice_number(self, mock_session):
        self.client.post(
            url_for("payments_stripe.pay", donation=False),
            data={
                "amount": "100",
                "currency": "usd",
                "recurring": "y",
            },
        )

        call_kwargs = mock_session.create.call_args[1]
        metadata = call_kwargs["subscription_data"]["metadata"]
        self.assertNotIn("invoice_number", metadata)

    @patch("stripe.checkout.Session")
    def test_recurring_payment_with_invoice_number(self, mock_session):
        self.client.post(
            url_for("payments_stripe.pay", donation=False),
            data={
                "amount": "100",
                "currency": "usd",
                "recurring": "y",
                "invoice_number": "42",
            },
        )

        call_kwargs = mock_session.create.call_args[1]
        metadata = call_kwargs["subscription_data"]["metadata"]
        self.assertEqual(metadata["invoice_number"], 42)

    @patch("stripe.checkout.Session")
    def test_one_time_payment_includes_supporter_id(self, mock_session):
        supporter = self._create_supporter()
        self.temporary_login(supporter.user)
        self.client.post(
            url_for("payments_stripe.pay", donation=False),
            data={
                "amount": "100",
                "currency": "usd",
                "invoice_number": "42",
            },
        )

        call_kwargs = mock_session.create.call_args[1]
        metadata = call_kwargs["payment_intent_data"]["metadata"]
        self.assertEqual(metadata["supporter_id"], supporter.id)

    @patch("stripe.checkout.Session")
    def test_recurring_payment_includes_supporter_id(self, mock_session):
        supporter = self._create_supporter()
        self.temporary_login(supporter.user)
        self.client.post(
            url_for("payments_stripe.pay", donation=False),
            data={
                "amount": "100",
                "currency": "usd",
                "recurring": "y",
            },
        )

        call_kwargs = mock_session.create.call_args[1]
        metadata = call_kwargs["subscription_data"]["metadata"]
        self.assertEqual(metadata["supporter_id"], supporter.id)

    @patch("stripe.checkout.Session")
    def test_donation_does_not_include_supporter_id(self, mock_session):
        supporter = self._create_supporter()
        self.temporary_login(supporter.user)
        self.client.post(
            url_for("payments_stripe.pay", donation=True),
            data={
                "amount": "100",
                "currency": "usd",
                "editor": "tester",
            },
        )

        call_kwargs = mock_session.create.call_args[1]
        metadata = call_kwargs["payment_intent_data"]["metadata"]
        self.assertNotIn("supporter_id", metadata)


class StripeWebhookViewTestCase(FlaskTestCase):
    """Tests for the inbound Stripe webhook.

    These drive the endpoint the way Stripe does: a signed JSON body. That makes
    stripe.Webhook.construct_event deserialise the payload for real, so the event
    reaching the view is a StripeObject rather than a dict we made up.
    """

    WEBHOOK_SECRET = "whsec_test_secret"

    @classmethod
    def create_app(cls):
        app = super().create_app()
        app.config["WTF_CSRF_ENABLED"] = False
        return app

    def setUp(self):
        super().setUp()
        for currency in ("USD", "EUR"):
            self.app.config["STRIPE_KEYS"][currency]["WEBHOOK_SECRET"] = self.WEBHOOK_SECRET

    def post_event(self, event, currency="usd", secret=None):
        """POST an event with a valid Stripe-Signature header, as Stripe would."""
        payload = json.dumps(event)
        timestamp = int(time.time())
        signature = hmac.new(
            (secret or self.WEBHOOK_SECRET).encode("utf-8"),
            msg=f"{timestamp}.{payload}".encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        return self.client.post(
            url_for("payments_stripe.webhook", currency=currency),
            data=payload,
            content_type="application/json",
            headers={"Stripe-Signature": f"t={timestamp},v1={signature}"},
        )

    @staticmethod
    def checkout_session_completed(mode="payment"):
        return {
            "id": "evt_test_webhook",
            "object": "event",
            "created": int(time.time()),
            "type": "checkout.session.completed",
            "data": {"object": {
                "id": "cs_test_1",
                "object": "checkout.session",
                "mode": mode,
                "payment_intent": "pi_test_1",
            }},
        }

    def test_webhook_rejects_bad_signature(self):
        response = self.post_event(self.checkout_session_completed(), secret="whsec_wrong")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json, {"error": "invalid signature"})

    def test_webhook_rejects_unknown_currency(self):
        response = self.post_event(self.checkout_session_completed(), currency="gbp")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json, {"error": "invalid currency"})

    @patch("metabrainz.model.Payment.log_one_time_charge")
    def test_webhook_logs_one_time_charge(self, mock_log):
        response = self.post_event(self.checkout_session_completed())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})
        mock_log.assert_called_once()
        currency, session = mock_log.call_args[0]
        self.assertEqual(currency, "usd")
        self.assertEqual(session["payment_intent"], "pi_test_1")

    @patch("metabrainz.model.Payment.log_one_time_charge")
    def test_webhook_ignores_subscription_checkout_session(self, mock_log):
        response = self.post_event(self.checkout_session_completed(mode="subscription"))

        self.assertEqual(response.status_code, 200)
        mock_log.assert_not_called()

    @patch("metabrainz.model.Payment.log_subscription_charge")
    def test_webhook_logs_subscription_charge(self, mock_log):
        event = {
            "id": "evt_test_invoice",
            "object": "event",
            "created": int(time.time()),
            "type": "invoice.paid",
            "data": {"object": {"id": "in_test_1", "object": "invoice", "charge": "ch_test_1"}},
        }
        response = self.post_event(event, currency="eur")

        self.assertEqual(response.status_code, 200)
        mock_log.assert_called_once()
        self.assertEqual(mock_log.call_args[0][0], "eur")

    @patch("metabrainz.model.Payment.log_one_time_charge")
    def test_webhook_asks_stripe_to_retry_unsettled_charge(self, mock_log):
        mock_log.side_effect = StripeChargeNotReadyError("balance transaction missing")

        response = self.post_event(self.checkout_session_completed())

        # 5xx makes Stripe redeliver once the charge has settled.
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json, {"error": "charge not ready, please retry"})

    @patch("metabrainz.model.Payment.log_one_time_charge")
    def test_webhook_ignores_unhandled_event_types(self, mock_log):
        event = {
            "id": "evt_test_other",
            "object": "event",
            "created": int(time.time()),
            "type": "customer.created",
            "data": {"object": {"id": "cus_test_1", "object": "customer"}},
        }
        response = self.post_event(event)

        self.assertEqual(response.status_code, 200)
        mock_log.assert_not_called()
