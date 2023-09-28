import datetime
from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user
from metabrainz.model.supporter import Supporter

index_bp = Blueprint('index', __name__)


@index_bp.route('/')
def home():
    return render_template(
        'index/index.html',
        good_supporters=Supporter.get_featured(limit=4, with_logos=True),
        bad_supporters=Supporter.get_featured(in_deadbeat_club=True, limit=4),
    )


@index_bp.route('/about')
def about():
    return render_template('index/about.html')


@index_bp.route('/projects')
def projects():
    return render_template('index/projects.html')


@index_bp.route('/team')
def team():
    return render_template('index/team.html')


@index_bp.route('/contact')
def contact():
    # Dear intelligent people who hate advertisers:
    #   No, we have no plans to add advertising, SEO, or software monetization to any of our pages.
    #   We are sick of being constantly harassed by advertisers, so we are giving them a place
    #   to send their proposals to. We're never going to read them. We're never going to respond to
    #   any of the proposals. And the deadline will always be extended to next month. :)
    today = datetime.date.today()
    today += datetime.timedelta(31)
    ad_deadline = today.replace(day=1)
    return render_template('index/contact.html', ad_deadline=ad_deadline)


@index_bp.route('/social-contract')
def social_contract():
    return render_template('index/social-contract.html')


@index_bp.route('/code-of-conduct')
def code_of_conduct():
    return render_template('index/code-of-conduct.html')


@index_bp.route('/conflict-policy')
def conflict_policy():
    return render_template('index/conflict-policy.html')


@index_bp.route('/sponsors')
def sponsors():
    return render_template('index/sponsors.html')


@index_bp.route('/bad-customers')
def bad_customers():
    return render_template(
        'index/bad-customers.html',
        bad_supporters=Supporter.get_featured(in_deadbeat_club=True),
    )


@index_bp.route('/privacy')
def privacy_policy():
    return render_template('index/privacy.html')


@index_bp.route('/gdpr')
def gdpr_statement():
    return render_template('index/gdpr.html')


@index_bp.route("/signup-options")
def signup_options():
    return render_template('index/signup-options.html')


@index_bp.route('/about/customers.html')
def about_customers_redirect():
    return redirect(url_for('supporters.supporters_list'), 301)


@index_bp.route('/shop')
def shop():
    return render_template('index/shop.html')


@index_bp.route('/datasets')
def datasets():
    return render_template('index/datasets.html')


@index_bp.route('/datasets/postgres-dumps')
def postgres_dumps():
    return render_template('index/datasets/postgres-dumps.html')


@index_bp.route('/datasets/derived-dumps')
def derived_dumps():
    return render_template('index/datasets/derived-dumps.html')


@index_bp.route('/datasets/signup')
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("index.download"))

    return render_template('index/datasets/signup.html')


@index_bp.route('/datasets/download')
def download():
    return render_template('index/datasets/download.html')
