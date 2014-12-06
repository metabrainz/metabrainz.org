from flask import Blueprint, render_template
from metabrainz.model.tier import Tier

index_bp = Blueprint('index', __name__)


@index_bp.route('/')
def home():
    return render_template('home.html')


@index_bp.route('/customers')
def customers():
    return render_template('about/customers.html', tiers=Tier.get_all())


@index_bp.route('/sponsors')
def sponsors():
    return render_template('about/sponsors.html')


@index_bp.route('/white-papers')
def white_papers():
    return render_template('about/white_papers.html')


@index_bp.route('/privacy')
def privacy_policy():
    return render_template('about/privacy.html')


@index_bp.route('/contact')
def contact():
    return render_template('contact.html')
