from flask import Blueprint, request, current_app
from metabrainz.model.donation import Donation
import requests

donations_paypal_bp = Blueprint('donations_paypal', __name__)


@donations_paypal_bp.route('/ipn', methods=['POST'])
def ipn():
    """Endpoint that receives Instant Payment Notifications (IPNs) from PayPal.

    Specifications are available at https://developer.paypal.com/docs/classic/ipn/integration-guide/IPNImplementation/.
    """
    if current_app.config['PAYMENT_PRODUCTION']:
        paypal_url = 'https://www.paypal.com/cgi-bin/webscr'
    else:
        paypal_url = 'https://www.sandbox.paypal.com/cgi-bin/webscr'

    # Checking if data is legit
    verification_response = requests.post(paypal_url, data='cmd=_notify-validate&'+str(request.get_data()))
    if verification_response.text == 'VERIFIED':
        Donation.process_paypal_ipn(request.form)

    return '', 200
