from metabrainz.testing import FlaskTestCase
from metabrainz.payments.forms import PaymentForm
from werkzeug.datastructures import MultiDict


class PaymentFormTestCase(FlaskTestCase):

    def _make_form(self, data):
        return PaymentForm(MultiDict(data), meta={"csrf": False})

    def test_one_time_payment_requires_invoice_number(self):
        """Invoice number is required for one-time (non-recurring) payments."""
        form = self._make_form({
            "amount": "100",
            "currency": "usd",
        })
        self.assertFalse(form.validate())
        self.assertIn("invoice_number", form.errors)

    def test_one_time_payment_with_invoice_number(self):
        """One-time payment with invoice number should be valid."""
        form = self._make_form({
            "amount": "100",
            "currency": "usd",
            "invoice_number": "42",
        })
        self.assertTrue(form.validate())

    def test_recurring_payment_without_invoice_number(self):
        """Invoice number is optional for recurring payments."""
        form = self._make_form({
            "amount": "100",
            "currency": "usd",
            "recurring": "y",
        })
        self.assertTrue(form.validate())

    def test_recurring_payment_with_invoice_number(self):
        """Recurring payment with invoice number should also be valid."""
        form = self._make_form({
            "amount": "100",
            "currency": "usd",
            "recurring": "y",
            "invoice_number": "42",
        })
        self.assertTrue(form.validate())
