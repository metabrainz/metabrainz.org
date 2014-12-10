from flask import Blueprint, render_template
from metabrainz.model.tier import Tier
from metabrainz.model.organization import Organization

index_bp = Blueprint('index', __name__)


@index_bp.route('/')
def home():
    featured_orgs = Organization.get_featured()
    # TODO: Randomize featured_orgs
    # TODO: Select only 4 featured_orgs
    return render_template('home.html', featured_orgs=featured_orgs)


@index_bp.route('/about')
def about():
    return render_template('about/index.html')


@index_bp.route('/customers')
def customers():
    return render_template('about/customers.html', tiers=Tier.get_all())


@index_bp.route('/sponsors')
def sponsors():
    return render_template('about/sponsors.html')


@index_bp.route('/privacy')
def privacy_policy():
    return render_template('about/privacy.html')
