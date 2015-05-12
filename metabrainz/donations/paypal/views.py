from flask import Blueprint, request, current_app
from werkzeug.datastructures import ImmutableOrderedMultiDict
from metabrainz.model.donation import Donation
from itertools import chain
import requests

donations_paypal_bp = Blueprint('donations_paypal', __name__)

PAYPAL_URL_PRIMARY = 'https://www.paypal.com/cgi-bin/webscr'
PAYPAL_URL_SANDBOX = 'https://www.sandbox.paypal.com/cgi-bin/webscr'

IPN_VERIFY_EXTRA_PARAMS = (('cmd', '_notify-validate'),)


@donations_paypal_bp.route('/ipn', methods=['POST'])
def ipn():
    """Endpoint that receives Instant Payment Notifications (IPNs) from PayPal.

    Specifications are available at https://developer.paypal.com/docs/classic/ipn/integration-guide/IPNImplementation/.
    """
    request.parameter_storage_class = ImmutableOrderedMultiDict

    # Checking if data is legit
    paypal_url = PAYPAL_URL_PRIMARY if current_app.config['PAYMENT_PRODUCTION'] else PAYPAL_URL_SANDBOX
    verify_args = chain(request.form.iteritems(), IPN_VERIFY_EXTRA_PARAMS)
    verify_string = '&'.join(('%s=%s' % (param, value) for param, value in verify_args))
    verification_response = requests.post(paypal_url, data=verify_string)

    if verification_response.text == 'VERIFIED':
        Donation.process_paypal_ipn(request.form)

    return '', 200
