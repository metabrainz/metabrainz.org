from __future__ import division
from flask import Blueprint, request, render_template, url_for, redirect, current_app, flash, jsonify
from metabrainz.model.donation import Donation
from metabrainz.donations.forms import DonationForm
from math import ceil
import requests
from requests.exceptions import RequestException

donations_bp = Blueprint('donations', __name__)


@donations_bp.route('/')
def index():
    if current_app.config['PAYMENT_PRODUCTION']:
        stripe_public_key = current_app.config['STRIPE_KEYS']['PUBLISHABLE']
    else:
        stripe_public_key = current_app.config['STRIPE_TEST_KEYS']['PUBLISHABLE']

    return render_template('donations/donate.html', form=DonationForm(),
                           stripe_public_key=stripe_public_key)


@donations_bp.route('/donors')
def donors():
    page = int(request.args.get('page', default=1))
    if page < 1:
        return redirect(url_for('.donors'))
    limit = 30
    offset = (page - 1) * limit

    order = request.args.get('order', default='date')
    if order == 'date':
        count, donations = Donation.get_recent_donations(limit=limit, offset=offset)
    elif order == 'amount':
        count, donations = Donation.get_biggest_donations(limit=limit, offset=offset)
    else:
        return redirect(url_for('.donors'))

    last_page = int(ceil(count / limit))
    if last_page != 0 and page > last_page:
        return redirect(url_for('.donors', page=last_page))

    return render_template('donations/donors.html', donations=donations,
                           page=page, last_page=last_page, order=order)


@donations_bp.route('/nag-check/<editor>')
def nag_check(editor):
    a, b = Donation.get_nag_days(editor)
    return '%s,%s\n' % (a, b)


@donations_bp.route('/check-editor/')
def check_editor():
    """Endpoint for checking if editor exists."""
    editor = request.args.get('q')
    if editor is None:
        return jsonify({'error': 'Editor not specified.'}), 400

    try:
        resp = requests.get('https://musicbrainz.org/ws/js/editor/?q=' + request.args.get('q')).json()
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


# DONATION RESULTS

@donations_bp.route('/complete', methods=['GET', 'POST'])
def complete():
    """Endpoint for successful donations."""
    flash("Thank you for making a donation to the MetaBrainz Foundation. Your "
          "support is greatly appreciated!", 'success')
    return redirect(url_for('donations.donors'))

@donations_bp.route('/cancelled')
def cancelled():
    """Endpoint for cancelled donations."""
    flash("We're sorry to see that you won't be donating today. We hope that "
          "you'll change your mind!")
    return redirect(url_for('donations.index'))

@donations_bp.route('/error')
def error():
    """Error page for donations.

    Users should be redirected there when errors occur during payment process.
    """
    flash("We're sorry, but it appears we've run into an error and can't "
          "process your donation.", 'error')
    return redirect(url_for('donations.index'))
