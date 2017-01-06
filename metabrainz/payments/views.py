from __future__ import division
from flask import Blueprint, request, render_template, url_for, redirect, current_app, jsonify
from flask_babel import gettext
from metabrainz.model.payment import Payment
from metabrainz.payments.forms import DonationForm, PaymentForm
from metabrainz import flash
from math import ceil
import requests
from requests.exceptions import RequestException

payments_bp = Blueprint('payments', __name__)


@payments_bp.route('/donate')
def donate():
    """Regular donation page."""
    if current_app.config['PAYMENT_PRODUCTION']:
        stripe_public_key = current_app.config['STRIPE_KEYS']['PUBLISHABLE']
    else:
        stripe_public_key = current_app.config['STRIPE_TEST_KEYS']['PUBLISHABLE']

    return render_template('payments/donate.html', form=DonationForm(),
                           stripe_public_key=stripe_public_key)


@payments_bp.route('/payment')
def payment():
    """Payment page for organizations."""
    if current_app.config['PAYMENT_PRODUCTION']:
        stripe_public_key = current_app.config['STRIPE_KEYS']['PUBLISHABLE']
    else:
        stripe_public_key = current_app.config['STRIPE_TEST_KEYS']['PUBLISHABLE']

    return render_template('payments/payment.html', form=PaymentForm(),
                           stripe_public_key=stripe_public_key)


@payments_bp.route('/donors')
def donors():
    page = int(request.args.get('page', default=1))
    if page < 1:
        return redirect(url_for('.donors'))
    limit = 30
    offset = (page - 1) * limit

    order = request.args.get('order', default='date')
    if order == 'date':
        count, donations = Payment.get_recent_donations(limit=limit, offset=offset)
    elif order == 'amount':
        count, donations = Payment.get_biggest_donations(limit=limit, offset=offset)
    else:
        return redirect(url_for('.donors'))

    last_page = int(ceil(count / limit))
    if last_page != 0 and page > last_page:
        return redirect(url_for('.donors', page=last_page))

    return render_template('payments/donors.html', donations=donations,
                           page=page, last_page=last_page, order=order)


@payments_bp.route('/cancel-recurring')
def cancel_recurring():
    return render_template('payments/cancel_recurring.html')


@payments_bp.route('/donations/nag-check/<editor>')
def nag_check(editor):
    a, b = Payment.get_nag_days(editor)
    return '%s,%s\n' % (a, b)


@payments_bp.route('/donate/check-editor/')
def check_editor():
    """Endpoint for checking if editor exists."""
    editor = request.args.get('q')
    if editor is None:
        return jsonify({'error': 'Editor not specified.'}), 400

    try:
        resp = requests.get(current_app.config['MUSICBRAINZ_BASE_URL'] +
                            'ws/js/editor/?q=' + request.args.get('q')).json()
    except RequestException as e:
        return jsonify({'error': e})

    found = False
    for item in resp:
        if 'name' in item:
            if item['name'].lower() == editor.lower():
                found = True
                break

    return jsonify({
        'editor': editor,
        'found': found,
    })


# PAYMENT RESULTS

@payments_bp.route('/payment/complete', methods=['GET', 'POST'])
def complete():
    """Endpoint for successful payments."""
    if request.args.get("is_donation") == "True":
        flash.success(gettext(
            "Thank you for making a donation to the MetaBrainz Foundation. Your "
            "support is greatly appreciated! It may take some time before your "
            "donation appears in the list due to processing delays."
        ))
        return redirect(url_for('payments.donors'))
    else:
        flash.success(gettext(
            "Thank you for making a payment to the MetaBrainz Foundation. Your "
            "support is greatly appreciated!"
        ))
        return redirect(url_for('financial_reports.index'))


@payments_bp.route('/payment/cancelled')
def cancelled():
    """Endpoint for cancelled payments."""
    if request.args.get("is_donation") == "True":
        flash.info(gettext(
            "We're sorry to see that you won't be donating today. We hope that "
            "you'll change your mind!"
        ))
        return redirect(url_for('payments.donate'))
    else:
        flash.info(gettext(
            "We're sorry to see that you won't be paying today. We hope that "
            "you'll change your mind!"
        ))
        return redirect(url_for('financial_reports.index'))


@payments_bp.route('/payment/error')
def error():
    """Error page for payments.

    Users should be redirected there when errors occur during payment process.
    """
    if request.args.get("is_donation") == "True":
        flash.error(gettext(
            "We're sorry, but it appears we've run into an error and can't "
            "process your donation."
        ))
        return redirect(url_for('payments.donate'))
    else:
        flash.error(gettext(
            "We're sorry, but it appears we've run into an error and can't "
            "process your payment."
        ))
        return redirect(url_for('financial_reports.index'))
