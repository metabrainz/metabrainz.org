from flask import Blueprint, render_template
from metabrainz.model.user import User

index_bp = Blueprint('index', __name__)


@index_bp.route('/')
def home():
    return render_template('index/index.html', featured_orgs=User.get_featured(4))


@index_bp.route('/about')
def about():
    return render_template('index/about.html')


@index_bp.route('/contact')
def contact():
    return render_template('index/contact.html')


@index_bp.route('/sponsors')
def sponsors():
    return render_template('index/sponsors.html')


@index_bp.route('/privacy')
def privacy_policy():
    return render_template('index/privacy.html')
