import datetime
import json

from flask import Blueprint, render_template, redirect, url_for, make_response
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf

from metabrainz import flash
from metabrainz.index.forms import CommercialSupporterEditForm, NonCommercialSupporterEditForm, UserEditForm
from metabrainz.model import Dataset, db
from metabrainz.model.supporter import Supporter
from metabrainz.model.user import User
from metabrainz.user.email import send_verification_email

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


@index_bp.route('/funding.json')
def funding_json():
    r = make_response(render_template('index/funding.json'))
    r.mimetype = 'application/json'
    return r


@index_bp.route('/profile')
@login_required
def profile():
    user = {
        "name": current_user.name,
        "email": current_user.get_email_any(),
        "is_email_confirmed": current_user.is_email_confirmed()
    }

    if current_user.supporter:
        supporter = current_user.supporter
        user["supporter"] = {
            "is_commercial": supporter.is_commercial,
            "state": supporter.state,
            "contact_name": supporter.contact_name,
            "org_name": supporter.org_name,
            "website_url": supporter.website_url,
            "api_url": supporter.api_url,
            "datasets": [
                {
                    "id": d.id,
                    "name": d.name,
                    "description": d.description
                } for d in supporter.datasets
            ],
            "good_standing": supporter.good_standing
        }
        if supporter.token:
            user["supporter"]["token"] = supporter.token.value
        else:
            user["supporter"]["token"] = None

        if supporter.is_commercial:
            user["supporter"]["tier"] = {
                "name": supporter.tier.name
            }
        else:
            user["supporter"]["tier"] = None

    return render_template('index/profile.html', props=json.dumps({
        "user": user,
        "csrf_token": generate_csrf() if not user["is_email_confirmed"] else None,
    }))


@index_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    available_datasets = []

    if current_user.supporter:
        if current_user.supporter.is_commercial:
            form = CommercialSupporterEditForm()
        else:
            available_datasets = Dataset.query.all()
            form = NonCommercialSupporterEditForm(available_datasets)
    else:
        form = UserEditForm()

    if form.validate_on_submit():
        if current_user.email != form.email.data:
            user = User.get(email=form.email.data)
            if user is None:
                current_user.unconfirmed_email = form.email.data
                db.session.commit()
                flash.success(f"Email verification link sent to {form.email.data}")
                send_verification_email(
                    current_user,
                    "Please verify your email address",
                    "email/user-email-address-verification.txt"
                )
            else:
                form.email.errors.append(
                    f"The given email address ({form.email.data}) is associated with a different account."
                )

        if current_user.supporter:
            kwargs = {
                "contact_name": form.contact_name.data,
            }
            if not current_user.supporter.is_commercial:
                kwargs["datasets"] = form.datasets.data
            current_user.supporter.update(**kwargs)

    form_data = {"email": current_user.email}
    if current_user.supporter:
        form_data["contact_name"] = current_user.supporter.contact_name
        if current_user.supporter.is_commercial:
            form_data["datasets"] = []
        else:
            form_data["datasets"] = [dataset.id for dataset in current_user.datasets]

    return render_template("index/profile-edit.html", props=json.dumps({
        "datasets": [{"id": d.id, "description": d.description, "name": d.name} for d in available_datasets],
        "is_supporter": current_user.supporter is not None,
        "is_commercial": current_user.supporter is not None and current_user.supporter.is_commercial,
        "csrf_token": generate_csrf(),
        "initial_form_data": form_data,
        "initial_errors": form.props_errors
    }))
