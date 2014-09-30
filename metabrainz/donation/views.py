from flask import Blueprint, request, render_template, url_for, redirect
from forms import WePayForm
from wepay import WePay
from flask import current_app

donation_bp = Blueprint('donation', __name__)


@donation_bp.route('/')
def index():
    return render_template('donation/donate.html')


@donation_bp.route('/paypal')
def paypal():
    """Donation page for PayPal."""
    # TODO: Implement donation page for PayPal!
    return "Not implemented!"


@donation_bp.route('/wepay', methods=['GET', 'POST'])
def wepay():
    """Donation page for WePay.

    We use official Python SDK to make API calls. Its source code is available at
    https://github.com/wepay/Python-SDK. Description of all WePay API endpoints and
    much more useful information is available at https://www.wepay.com/developer/reference/.

    Users can make two types of donations:
    - one time single payment (https://www.wepay.com/developer/reference/checkout)
    - recurring monthly donation (https://www.wepay.com/developer/reference/preapproval)
    """
    recur = request.args.get('recur') == '1'
    amount = request.args.get('amount') or 0

    form = WePayForm(float(amount))

    if form.validate_on_submit():
        operation_type = 'preapproval' if recur else 'checkout'

        wepay = WePay(production=current_app.config['PAYMENT_PRODUCTION'],
                      access_token=current_app.config['WEPAY_ACCESS_TOKEN'])

        params = {
            'account_id': current_app.config['WEPAY_ACCOUNT_ID'],
            'amount': float(form.amount.data),
            'redirect_uri': url_for('.complete', _external=True),
            'mode': 'regular',
            'require_shipping': True,
        }

        # Setting parameters that are specific for selected type of donation
        if recur:
            params['period'] = 'monthly'
            params['auto_recur'] = True
            params['short_description'] = 'Recurring donation to MetaBrainz Foundation'
        else:
            params['type'] = 'DONATION'
            params['short_description'] = 'Donation to MetaBrainz Foundation'

        response = wepay.call('/%s/create' % operation_type, params)

        if 'error' in response:
            return redirect(url_for('.error'))
        else:
            return redirect(response['%s_uri' % operation_type])

    return render_template('donation/wepay.html', form=form, recur=recur)


@donation_bp.route('/wepay/ipn', methods=['POST'])
def wepay_ipn():
    # TODO: Verify and log WePay checkout.
    return "Not implemented!"


@donation_bp.route('/complete')
def complete():
    """Endpoint for successful donations."""
    return render_template('donation/complete.html')


@donation_bp.route('/error')
def error():
    """Error page for donations.

    Users should be redirected there when errors occur during payment process.
    """
    return render_template('donation/error.html')

