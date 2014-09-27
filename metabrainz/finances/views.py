from flask import Blueprint, render_template

finances_bp = Blueprint('finances', __name__)


@finances_bp.route('/')
def index():
    # TODO: Create this page.
    return "Page is missing."


@finances_bp.route('/donations')
def donations():
    # TODO: Create this page.
    return "Page is missing."


@finances_bp.route('/donations/by-amount')
def highest_donors():
    # TODO: Create this page.
    return "Page is missing."


@finances_bp.route('/historical')
def historical():
    return render_template('finances/historical.html')
