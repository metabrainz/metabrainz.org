from flask import Blueprint, render_template

donation_bp = Blueprint('donation', __name__)


@donation_bp.route('/')
def index():
    return render_template('donation/donate.html')


@donation_bp.route('/paypal')
def paypal():
    # TODO: Implement!
    return "Not implemented!"


@donation_bp.route('/wepay')
def wepay():
    # TODO: Implement!
    return "Not implemented!"
