from flask import Blueprint, request, current_app, redirect, url_for
from metabrainz.payments.forms import DonationForm, PaymentForm
from metabrainz.model.payment import Payment
import stripe

payments_stripe_bp = Blueprint('payments_stripe', __name__)


@payments_stripe_bp.route('/', methods=['POST'])
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
        return redirect(url_for('payments.error', is_donation=is_donation))

    if current_app.config['PAYMENT_PRODUCTION']:
        stripe.api_key = current_app.config['STRIPE_KEYS']['SECRET']
    else:
        stripe.api_key = current_app.config['STRIPE_TEST_KEYS']['SECRET']

    # Get the credit card details submitted by the form
    token = request.form['stripeToken']

    charge_metadata = {
        'email': request.form['stripeEmail'],
        'is_donation': is_donation,
    }
    if is_donation:
        charge_description = "Donation to the MetaBrainz Foundation"
        # Using DonationForm
        charge_metadata['editor'] = form.editor.data
        charge_metadata['anonymous'] = form.anonymous.data
        charge_metadata['can_contact'] = form.can_contact.data
    else:
        charge_description = "Payment to the MetaBrainz Foundation"
        # Using PaymentForm
        charge_metadata['invoice_number'] = form.invoice_number.data

    # Create the charge on Stripe's servers - this will charge the donor's card
    try:
        charge = stripe.Charge.create(
            amount=int(form.amount.data * 100),  # amount in cents
            currency='USD',
            card=token,
            description=charge_description,
            metadata=charge_metadata,
        )
    except stripe.CardError:
        # The card has been declined
        return redirect(url_for('payments.error', is_donation=is_donation))

    Payment.log_stripe_charge(charge)

    return redirect(url_for('payments.complete', is_donation=is_donation))
