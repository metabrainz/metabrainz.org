from metabrainz.donations import forms
from flask import Blueprint, request, url_for, redirect, current_app
from werkzeug.exceptions import BadRequest, InternalServerError
from wepay import WePay
from metabrainz.model.donation import Donation

donations_wepay_bp = Blueprint('donations_wepay', __name__)


@donations_wepay_bp.route('/', methods=['POST'])
def donate():
    """Donation processor for WePay.

    We use official Python SDK to make API calls. Its source code is available at
    https://github.com/wepay/Python-SDK. Description of all WePay API endpoints and
    much more useful information is available at https://www.wepay.com/developer/reference/.

    Users can make two types of donations:
    - one time single payment (https://www.wepay.com/developer/reference/checkout)
    - recurring monthly donation (https://www.wepay.com/developer/reference/preapproval)
    """

    form = forms.DonationForm()

    if not form.validate():
        return redirect(url_for('donations.error'))

    operation_type = 'preapproval' if form.recurring.data is True else 'checkout'

    wepay = WePay(production=current_app.config['PAYMENT_PRODUCTION'],
                  access_token=current_app.config['WEPAY_ACCESS_TOKEN'])

    params = {
        'account_id': current_app.config['WEPAY_ACCOUNT_ID'],
        'amount': float(form.amount.data),
        'redirect_uri': url_for('donations.complete', _external=True),
        'mode': 'regular',
        'require_shipping': True,
    }

    # Setting callback_uri that will receive IPNs if endpoint is not local
    if not (request.headers['Host'].startswith('localhost') or request.headers['Host'].startswith('127.0.0.1')):
        # Also passing arguments that will be returned with IPNs
        params['callback_uri'] = url_for('.ipn', _external=True,
                                         editor=form.editor.data,
                                         anonymous=form.anonymous.data,
                                         can_contact=form.can_contact.data)

    # Setting parameters that are specific for selected type of donation
    if form.recurring.data is True:
        params['period'] = 'monthly'
        params['auto_recur'] = True
        params['short_description'] = 'Recurring donation to MetaBrainz Foundation'
    else:
        params['type'] = 'DONATION'
        params['short_description'] = 'Donation to MetaBrainz Foundation'

    response = wepay.call('/%s/create' % operation_type, params)

    if 'error' in response:
        return redirect(url_for('donations.error'))
    else:
        return redirect(response['%s_uri' % operation_type])


@donations_wepay_bp.route('/ipn', methods=['POST'])
def ipn():
    """Endpoint that receives Instant Payment Notifications (IPNs) from WePay.

    More info is available at https://www.wepay.com/developer/reference/ipn.
    """

    # Checking the type of object (should be `checkout`)
    if 'checkout_id' in request.form:
        checkout_id = request.form['checkout_id']
    else:
        raise BadRequest('Invalid object_id.')

    # Getting additional info that was passed with callback_uri during payment creation
    editor = request.args['editor']
    anonymous = request.args['anonymous']
    can_contact = request.args['can_contact']

    result = Donation.verify_and_log_wepay_checkout(checkout_id, editor, anonymous, can_contact)
    if result is True:
        return "Recorded."
    else:
        raise InternalServerError()
