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
    # TODO: Implement!
    return "Not implemented!"


@donation_bp.route('/wepay', methods=('GET', 'POST'))
def wepay():
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
            'redirect_uri': url_for('.wepay_callback', _external=True),
            'mode': 'regular',
            'require_shipping': True,
        }

        if recur:
            params['period'] = 'monthly'
            params['auto_recur'] = True
            params['short_description'] = 'Recurring donation to MetaBrainz Foundation'
        else:
            params['type'] = 'DONATION'
            params['short_description'] = 'Donation to MetaBrainz Foundation'

        response = wepay.call('/%s/create' % operation_type, params)

        if response['error']:
            return redirect(url_for('.error'))
        else:
            return redirect(response['%s_uri' % operation_type])

    return render_template('donation/wepay.html', form=form, recur=recur)


@donation_bp.route('/wepay/complete')
def wepay_callback():
    return render_template('donation/complete.html')


@donation_bp.route('/error')
def error():
    return render_template('donation/error.html')

