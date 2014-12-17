from flask import Blueprint, render_template
from metabrainz.model.organization import Organization

index_bp = Blueprint('index', __name__)


@index_bp.route('/')
def home():
    return render_template('index/index.html', featured_orgs=Organization.get_featured(4))


@index_bp.route('/about')
def about():
    return render_template('index/about.html')


@index_bp.route('/sponsors')
def sponsors():
    return render_template('index/sponsors.html')


@index_bp.route('/privacy')
def privacy_policy():
    return render_template('index/privacy.html')
