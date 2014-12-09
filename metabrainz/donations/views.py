from __future__ import division
from flask import Blueprint, request, render_template, url_for, redirect
from metabrainz.model.donation import Donation
from math import ceil

donations_bp = Blueprint('donations', __name__)


@donations_bp.route('/')
def index():
    """Home page for donations."""
    return render_template('donations/donate.html')


@donations_bp.route('/donors')
def donors():
    page = int(request.args.get('page', default=1))
    if page < 1:
        return redirect(url_for('.donations'))
    limit = 30
    offset = (page - 1) * limit
    count, donations = Donation.get_recent_donations(limit=limit, offset=offset)

    last_page = int(ceil(count / limit))
    if page > last_page:
        return redirect(url_for('.donations', page=last_page))

    return render_template('donations/donors.html', donations=donations,
                           page=page, last_page=last_page)


@donations_bp.route('/highest-donors')
def highest_donors():
    page = int(request.args.get('page', default=1))
    if page < 1:
        return redirect(url_for('.highest_donors'))
    limit = 30
    offset = (page - 1) * limit
    count, donations = Donation.get_biggest_donations(limit=limit, offset=offset)

    last_page = int(ceil(count / limit))
    if page > last_page:
        return redirect(url_for('.highest_donors', page=last_page))

    return render_template('donations/donors_highest.html', donations=donations,
                           page=page, last_page=last_page)


@donations_bp.route('/nag-check/<editor>')
def nag_check(editor):
    a, b = Donation.get_nag_days(editor)
    return '%s,%s\n' % (a, b)


# DONATION RESULTS

@donations_bp.route('/complete', methods=['GET', 'POST'])
def complete():
    """Endpoint for successful donations."""
    return render_template('donations/results/complete.html')

@donations_bp.route('/cancelled')
def cancelled():
    """Endpoint for cancelled donations."""
    return render_template('donations/results/cancelled.html')

@donations_bp.route('/error')
def error():
    """Error page for donations.

    Users should be redirected there when errors occur during payment process.
    """
    return render_template('donations/results/error.html')
