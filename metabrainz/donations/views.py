from flask import Blueprint, render_template
from metabrainz.model.donation import Donation

donations_bp = Blueprint('donations', __name__)


@donations_bp.route('/')
def index():
    """Home page for donations."""
    return render_template('donations/donate.html')


@donations_bp.route('/nag-check/<editor>')
def nag_check(editor):
    a, b = Donation.get_nag_days(editor)
    return '%s,%s\n' % (a, b)


# DONATION RESULTS

@donations_bp.route('/complete', methods=['GET', 'POST'])
def complete():
    """Endpoint for successful donations."""
    return render_template('donations/complete.html')

@donations_bp.route('/cancelled')
def cancelled():
    """Endpoint for cancelled donations."""
    return render_template('donations/cancelled.html')

@donations_bp.route('/error')
def error():
    """Error page for donations.

    Users should be redirected there when errors occur during payment process.
    """
    return render_template('donations/error.html')
