from flask import Blueprint, request
from metabrainz.model.payment import Payment

payments_wepay_bp = Blueprint('payments_wepay', __name__)


# TODO(roman): Remove this later after deployment of initial removal to make sure that all IPNs go through.
@payments_wepay_bp.route('/ipn', methods=['POST'])
def ipn():
    """Endpoint that receives Instant Payment Notifications (IPNs) from WePay.

    More info is available at https://www.wepay.com/developer/reference/ipn.
    """

    # Checking the type of object (should be `checkout`)
    if 'checkout_id' in request.form:
        checkout_id = request.form['checkout_id']
    else:
        # No need to return any errors in this case
        # TODO: Add logging there.
        return 'Invalid object_id.', 200

    # Getting additional info that was passed with callback_uri during payment creation
    if 'is_donation' in request.args and request.args['is_donation'] != 'True':
        result = Payment.verify_and_log_wepay_checkout(
            checkout_id=checkout_id,
            is_donation=False,
            invoice_number=int(request.args['invoice_number']),
        )
    else:
        result = Payment.verify_and_log_wepay_checkout(
            checkout_id=checkout_id,
            is_donation=True,
            editor=request.args['editor'],
            anonymous=request.args['anonymous'],
            can_contact=request.args['can_contact'],
        )

    if result is True:
        return "Recorded."

    return '', 200
