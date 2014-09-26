from flask import Blueprint, render_template

index_bp = Blueprint('index', __name__)


@index_bp.route('/')
def home():
    return render_template('home.html')


@index_bp.route('/customers')
def customers():
    # TODO: Create this page.
    return render_template('home.html')


@index_bp.route('/sponsors')
def sponsors():
    # TODO: Create this page.
    return render_template('home.html')


@index_bp.route('/press-releases')
def press_releases():
    # TODO: Create this page.
    return render_template('home.html')


@index_bp.route('/white-papers')
def white_papers():
    # TODO: Create this page.
    return render_template('home.html')


@index_bp.route('/privacy')
def privacy_policy():
    # TODO: Create this page.
    return render_template('home.html')


@index_bp.route('/contact')
def contact():
    return render_template('contact.html')
