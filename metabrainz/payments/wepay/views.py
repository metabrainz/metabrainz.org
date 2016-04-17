from metabrainz.payments import forms
from flask import Blueprint, request, url_for, redirect, current_app
from werkzeug.exceptions import BadRequest, InternalServerError
from wepay import WePay
from metabrainz.model.payment import Payment

payments_wepay_bp = Blueprint('payments_wepay', __name__)


@payments_wepay_bp.route('/', methods=['POST'])
def pay():
    """Payment processor for WePay.

    We use official Python SDK to make API calls. Its source code is available at
    https://github.com/wepay/Python-SDK. Description of all WePay API endpoints and
    much more useful information is available at https://www.wepay.com/developer/reference/.

    Users can make two types of donations:
    - one time single payment (https://www.wepay.com/developer/reference/checkout)
    - recurring monthly donation (https://www.wepay.com/developer/reference/preapproval)
    """
    is_donation = request.args.get('is_donation') == "True"

    if is_donation:
        form = forms.DonationForm()
    else:
        form = forms.PaymentForm()

    if not form.validate():
        return redirect(url_for('payments.error', is_donation=is_donation))

    operation_type = 'preapproval' if form.recurring.data is True else 'checkout'

    wepay = WePay(production=current_app.config['PAYMENT_PRODUCTION'],
                  access_token=current_app.config['WEPAY_ACCESS_TOKEN'])

    params = {
        'account_id': current_app.config['WEPAY_ACCOUNT_ID'],
        'amount': float(form.amount.data),
        'redirect_uri': url_for(
            'payments.complete',
            is_donation=is_donation,
            _external=True,
            _scheme=current_app.config['PREFERRED_URL_SCHEME'],
        ),
        'mode': 'regular',
        'require_shipping': True,
    }

    # Setting callback_uri that will receive IPNs if endpoint is not local
    if not (request.headers['Host'].startswith('localhost') or request.headers['Host'].startswith('127.0.0.1')):
        # Also passing arguments that will be returned with IPNs
        if is_donation:
            params['callback_uri'] = url_for(
                '.ipn',
                _external=True,
                _scheme=current_app.config['PREFERRED_URL_SCHEME'],
                is_donation=is_donation,
                editor=form.editor.data,
                anonymous=form.anonymous.data,
                can_contact=form.can_contact.data,
            )
        else:
            params['callback_uri'] = url_for(
                '.ipn',
                _external=True,
                _scheme=current_app.config['PREFERRED_URL_SCHEME'],
                is_donation=is_donation,
                invoice_number=form.invoice_number.data,
            )

    # Setting parameters that are specific for selected type of payment
    if is_donation:
        if form.recurring.data is True:
            params['period'] = 'monthly'
            params['auto_recur'] = True
            params['short_description'] = 'Recurring donation to the MetaBrainz Foundation'
        else:
            params['type'] = 'DONATION'
            params['short_description'] = 'Donation to the MetaBrainz Foundation'
    else:
        if form.recurring.data is True:
            params['period'] = 'monthly'
            params['auto_recur'] = True
            params['short_description'] = 'Recurring payment to the MetaBrainz Foundation'
        else:
            params['type'] = 'SERVICE'
            params['short_description'] = 'Payment to the MetaBrainz Foundation'

    response = wepay.call('/%s/create' % operation_type, params)

    if 'error' in response:
        return redirect(url_for('payments.error', is_donation=is_donation))
    else:
        return redirect(response['%s_uri' % operation_type])


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
