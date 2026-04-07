from unittest.mock import patch, MagicMock

from flask import url_for

from metabrainz.testing import FlaskTestCase


class StripePayViewTestCase(FlaskTestCase):

    @classmethod
    def create_app(cls):
        app = super().create_app()
        app.config['WTF_CSRF_ENABLED'] = False
        return app

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
