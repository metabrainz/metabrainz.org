from unittest.mock import patch, MagicMock

from flask import url_for

from metabrainz.model.supporter import Supporter
from metabrainz.testing import FlaskTestCase


class StripePayViewTestCase(FlaskTestCase):

    @classmethod
    def create_app(cls):
        app = super().create_app()
        app.config['WTF_CSRF_ENABLED'] = False
        return app

    def _create_supporter(self, **kwargs):
        defaults = dict(
            is_commercial=True,
            musicbrainz_id='test_user',
            musicbrainz_row_id=1,
            contact_name='Test User',
            contact_email='test@example.org',
            data_usage_desc='Testing',
        )
        defaults.update(kwargs)
        return Supporter.add(**defaults)

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
        self.temporary_login(supporter.id)
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
        self.temporary_login(supporter.id)
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
        self.temporary_login(supporter.id)
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
