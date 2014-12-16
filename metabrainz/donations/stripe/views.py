from flask import Blueprint, request, render_template, current_app
from metabrainz.donations.forms import DonationForm
from metabrainz.model.donation import Donation
import stripe

donations_stripe_bp = Blueprint('donations_stripe', __name__)


@donations_stripe_bp.route('/', methods=['POST'])
def donate():
    """Donation page for Stripe.

    Stripe API reference for Python can be found at https://stripe.com/docs/api/python.
    """
    form = DonationForm()
    if not form.validate():
        return render_template('donations/results/error.html')

    if current_app.config['PAYMENT_PRODUCTION']:
        stripe.api_key = current_app.config['STRIPE_KEYS']['SECRET']
    else:
        stripe.api_key = current_app.config['STRIPE_TEST_KEYS']['SECRET']

    # Get the credit card details submitted by the form
    token = request.form['stripeToken']

    # Create the charge on Stripe's servers - this will charge the donor's card
    try:
        charge = stripe.Charge.create(
            amount=int(form.amount.data * 100),  # amount in cents
            currency='USD',
            card=token,
            description='Donation to MetaBrainz Foundation',
            metadata={
                'email': request.form['stripeEmail'],
                'editor': form.editor.data,
                'anonymous': form.anonymous.data,
                'can_contact': form.can_contact.data,
            },
        )
    except stripe.CardError, e:
        # The card has been declined
        return render_template('donations/results/error.html')

    Donation.log_stripe_charge(charge)

    return render_template('donations/results/complete.html')
