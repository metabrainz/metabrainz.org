from flask import Blueprint, render_template

donation_bp = Blueprint('donation', __name__)


@donation_bp.route('/')
def index():
    # TODO: Create this page.
    return render_template('home.html')
