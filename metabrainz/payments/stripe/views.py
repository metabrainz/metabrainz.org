from flask import Blueprint, request, current_app, redirect, url_for, jsonify

from metabrainz.model import Payment
from metabrainz.payments.forms import DonationForm, PaymentForm
import stripe

payments_stripe_bp = Blueprint('payments_stripe', __name__)


@payments_stripe_bp.route("/", methods=["POST"])
def pay():
    """Payment page for Stripe.

    Stripe API reference for Python can be found at https://stripe.com/docs/api/python.
    """
    is_donation = request.args.get("donation") == "True"
    if is_donation:
        form = DonationForm()
    else:
        form = PaymentForm()

    if not form.validate():
        return redirect(url_for("payments.error", is_donation=is_donation))

    is_recurring = form.recurring.data

    charge_metadata = {
        "is_donation": is_donation,
    }
    if is_donation:  # Using DonationForm
        charge_metadata["editor"] = form.editor.data
        charge_metadata["anonymous"] = form.anonymous.data
        charge_metadata["can_contact"] = form.can_contact.data
        description = "Donation to the MetaBrainz Foundation"
    else:  # Using PaymentForm
        charge_metadata["invoice_number"] = form.invoice_number.data
        # Add invoice number to description only for non-recurring payments
        if is_recurring:
            description = "Payment to the MetaBrainz Foundation"
        else:
            description = f"Payment to the MetaBrainz Foundation for Invoice {form.invoice_number.data}"

    session_config = {
        "billing_address_collection": "required",
        "line_items": [
            {
                "price_data": {
                    "unit_amount": int(form.amount.data * 100),  # amount in cents
                    "currency": form.currency.data,
                    "product_data": {
                        "name": "Support the MetaBrainz Foundation",
                        "description": description
                    }
                },
                "quantity": 1
            }
        ],
        "payment_method_types": ["card"],
        "mode": "subscription",
        # stripe wants absolute urls so url_for doesn't suffice
        "success_url": f'{current_app.config["SERVER_BASE_URL"]}/payment/complete?is_donation={is_donation}',
        "cancel_url": f'{current_app.config["SERVER_BASE_URL"]}/payment/cancelled?is_donation={is_donation}',
    }

    if is_recurring:
        session_config["mode"] = "subscription"
        # configure monthly subscription
        session_config["line_items"][0]["price_data"]["recurring"] = {"interval": "month"}
        session_config["subscription_data"] = {"metadata": charge_metadata}
    else:
        session_config["mode"] = "payment"
        # submit_type and payment_intent_data are only allowed in payment mode
        session_config["submit_type"] = "donate" if is_donation else "pay"
        session_config["payment_intent_data"] = {
            "description": description,
            "metadata": charge_metadata
        }

    try:
        session = stripe.checkout.Session.create(**session_config)
        return redirect(session.url, code=303)
    except Exception as e:
        current_app.logger.error(e, exc_info=True)
        return redirect(url_for("payments.error", is_donation=is_donation))


@payments_stripe_bp.route("/webhook/", methods=["POST"])
def webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    webhook_secret = current_app.config["STRIPE_KEYS"]["WEBHOOK_SECRET"]

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        current_app.logger.error("Invalid Stripe Payload", exc_info=True)
        return jsonify({"error": "invalid payload"}), 400
    except stripe.error.SignatureVerificationError:
        current_app.logger.error("Stripe signature error, possibly fake event", exc_info=True)
        return jsonify({"error": "invalid signature"}), 400

    # for one time payments, mode is payment, and we use the checkout.session.completed event to log charges
    # other option is mode = subscription i.e. recurring payments, for which payment_intent data is unavailable
    # in this webhook. hence, we use invoice.paid event instead which contains it.
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        if session["mode"] == "payment":
            Payment.log_one_time_charge(session)
    elif event["type"] == "invoice.paid":
        Payment.log_subscription_charge(event["data"]["object"])

    return jsonify({"status": "ok"})
