from flask import Blueprint, request, render_template, current_app
from metabrainz.model.donation import Donation
import requests

donations_paypal_bp = Blueprint('donations_paypal', __name__)


@donations_paypal_bp.route('/')
def donate():
    """Donation page for PayPal.

    We use PayPal Payments Standard to receive donations. Form is submitted directly to
    PayPal, so we don't need to do processing there. More information about this functionality
    is avaukabke at https://developer.paypal.com/docs/classic/paypal-payments-standard/integration-guide/formbasics/.
    """
    recurring = request.args.get('recur') == '1'
    amount = request.args.get('amount') or 0
    return render_template('donations/paypal.html', recurring=recurring, amount=amount)


@donations_paypal_bp.route('/ipn', methods=['POST'])
def ipn():
    """Endpoint that receives Instant Payment Notifications (IPNs) from PayPal.

    Specifications are available at https://developer.paypal.com/docs/classic/ipn/integration-guide/IPNImplementation/.
    """
    data = request.get_data()

    if current_app.config['PAYMENT_PRODUCTION']:
        paypal_url = 'https://www.paypal.com/cgi-bin/webscr'
    else:
        paypal_url = 'https://www.sandbox.paypal.com/cgi-bin/webscr'

    # Checking if data is legit
    verification_response = requests.post(paypal_url, data='cmd=_notify-validate&'+data)
    if verification_response.text == 'VERIFIED':
        Donation.process_paypal_ipn(request.form)

    return '', 200
