import json
import logging

from flask import Blueprint, request, redirect, render_template, url_for, jsonify, current_app
from flask_babel import gettext
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf.csrf import generate_csrf
from werkzeug.exceptions import NotFound, BadRequest

from metabrainz import flash
from metabrainz.model import Dataset
from metabrainz.model.supporter import Supporter, InactiveSupporterException
from metabrainz.model.tier import Tier
from metabrainz.model.token import TokenGenerationLimitException
from metabrainz.model.user import User
from metabrainz.user import login_forbidden
from metabrainz.supporter.forms import CommercialSignUpForm, NonCommercialSignUpForm, CommercialSupporterEditForm, \
    NonCommercialSupporterEditForm
from metabrainz.user.email import send_verification_email

supporters_bp = Blueprint('supporters', __name__)

SESSION_KEY_ACCOUNT_TYPE = 'account_type'
SESSION_KEY_TIER_ID = 'account_tier'
SESSION_KEY_MB_USERNAME = 'mb_username'
SESSION_KEY_MB_EMAIL = 'mb_email'

ACCOUNT_TYPE_COMMERCIAL = 'commercial'
ACCOUNT_TYPE_NONCOMMERCIAL = 'noncommercial'


@supporters_bp.route('/supporters')
def supporters_list():
    return render_template('supporters/supporters-list.html', tiers=Tier.get_available(sort=True, sort_desc=True))


@supporters_bp.route('/supporters/bad')
def bad_standing():
    return render_template('supporters/bad-standing.html')


@supporters_bp.route('/supporters/account-type')
def account_type():
    return render_template(
        'supporters/account-type.html',
        tiers=Tier.get_available(sort=True),
        featured_supporters=Supporter.get_featured()
    )


@supporters_bp.route('/supporters/tiers/<int:tier_id>')
def tier(tier_id):
    t = Tier.get(id=tier_id)
    if not t or not t.available:
        raise NotFound(gettext("Can't find tier with a specified ID."))
    return render_template('supporters/tier.html', tier=t)

@supporters_bp.route('/signup')
@login_forbidden
def signup():
    mb_username = session.fetch_data(SESSION_KEY_MB_USERNAME)
    if mb_username is None:
        # Show template with a link to MusicBrainz OAuth page
        return render_template('supporters/mb-signup.html')

@supporters_bp.route('/signup/commercial', methods=('GET', 'POST'))
@login_forbidden
def signup_commercial():
    """Sign up endpoint for commercial supporters.

    Commercial supporters need to choose support tier before filling out the form.
    `tier_id` argument with ID of a tier of choice is required there.
    """
    tier_id = request.args.get('tier_id')
    if not tier_id:
        flash.warning(gettext("You need to choose support tier before signing up!"))
        return redirect(url_for('.account_type'))

    try:
       tier_id = int(tier_id)
    except ValueError:
        tier_id = 0

    selected_tier = Tier.get(id=tier_id)
    if not selected_tier or not selected_tier.available:
        flash.error(gettext("You need to choose existing tier before signing up!"))
        return redirect(url_for(".account_type"))

    form = CommercialSignUpForm()

    def custom_validation(f):
        if f.amount_pledged.data < selected_tier.price:
            flash.warning(gettext(
                "Custom amount must be more than threshold amount"
                "for selected tier or equal to it!"
            ))
            return False
        return True

    if form.validate_on_submit() and custom_validation(form):
        user = User.get(name=form.username.data)
        if user is not None:
            form.form_errors.append(f"Another user with username '{form.username.data}' exists.")
            return render_template("supporters/signup-commercial.html", form=form, tier=selected_tier)

        # TODO: Handle the case where multiple users sign up with same email but haven"t verified it yet
        user = User.get(email=form.email.data)
        if user is not None:
            form.form_errors.append(f"Another user with email '{form.email.data}' exists.")
            return render_template("supporters/signup-commercial.html", form=form, tier=selected_tier)

        user = User.add(name=form.username.data, email=form.email.data, password=form.password.data)

        new_supporter = Supporter.add(
            is_commercial=True,
            contact_name=form.contact_name.data,
            contact_email=form.contact_email.data,
            data_usage_desc=form.usage_desc.data,

            org_name=form.org_name.data,
            org_desc=form.org_desc.data,
            website_url=form.website_url.data,
            org_logo_url=form.logo_url.data,
            api_url=form.api_url.data,

            address_street=form.address_street.data,
            address_city=form.address_city.data,
            address_state=form.address_state.data,
            address_postcode=form.address_postcode.data,
            address_country=form.address_country.data,

            tier_id=tier_id,
            amount_pledged=form.amount_pledged.data,
            datasets=[],
            user=user
        )
        flash.success(gettext(
            "Thanks for signing up! Your application will be reviewed "
            "soon. We will send you updates via email."
        ))
        send_verification_email(
            user,
            "[MetaBrainz] Sign up confirmation",
            "email/supporter-commercial-welcome-email-address-verification.txt"
        )
        login_user(new_supporter)
        return redirect(url_for('.profile'))

    form_errors = {k: ". ".join(v) for k, v in form.errors.items()}
    form_data = dict(**form.data)
    if form_data["amount_pledged"]:
        form_data["amount_pledged"] = float(form_data["amount_pledged"])
    form_data.pop("csrf_token", None)

    return render_template("supporters/signup-commercial.html", props=json.dumps({
        "tier": {
            "name": selected_tier.name,
            "price": float(selected_tier.price)
        },
        "mb_username": mb_username,
        "recaptcha_site_key": current_app.config["RECAPTCHA_PUBLIC_KEY"],
        "csrf_token": generate_csrf(),
        "initial_form_data": form_data,
        "initial_errors": form_errors
    }))


@supporters_bp.route('/signup/noncommercial', methods=('GET', 'POST'))
@login_forbidden
def signup_noncommercial():
    """Sign up endpoint for non-commercial supporters."""
    available_datasets = Dataset.query.all()

    form = NonCommercialSignUpForm(available_datasets)
    if form.validate_on_submit():
        user = User.get(name=form.username.data)
        if user is not None:
            form.form_errors.append(f"Another user with username '{form.username.data}' exists.")
            return render_template("supporters/signup-non-commercial.html", form=form)

        # TODO: Handle the case where multiple users sign up with same email but haven"t verified it yet
        user = User.get(email=form.email.data)
        if user is not None:
            form.form_errors.append(f"Another user with email '{form.email.data}' exists.")
            return render_template("supporters/signup-non-commercial.html", form=form)

        user = User.add(name=form.username.data, email=form.email.data, password=form.password.data)
        supporter = Supporter.add(
            is_commercial=False,
            contact_name=form.contact_name.data,
            contact_email=form.contact_email.data,
            data_usage_desc=form.usage_desc.data,
            datasets=form.datasets.data,
            user=user
        )
        send_verification_email(
            user,
            "[MetaBrainz] Sign up confirmation",
            "email/supporter-noncommercial-welcome-email-address-verification.txt"
        )
        flash.success(gettext("Thanks for signing up! Please check your inbox to complete verification."))

        login_user(user)
        return redirect(url_for('.profile'))

    form_errors = {k: ". ".join(v) for k, v in form.errors.items()}
    form_data = dict(**form.data)
    form_data.pop("csrf_token", None)

    return render_template("supporters/signup-non-commercial.html", props=json.dumps({
        "datasets": [{"id": d.id, "description": d.description, "name": d.name} for d in available_datasets],
        "mb_username": mb_username,
        "recaptcha_site_key": current_app.config["RECAPTCHA_PUBLIC_KEY"],
        "csrf_token": generate_csrf(),
        "initial_form_data": form_data,
        "initial_errors": form_errors
    }))


@supporters_bp.route('/login/musicbrainz')
@login_forbidden
def musicbrainz():
    session.session['next'] = request.args.get('next')
    return redirect(musicbrainz_login.get_authentication_uri())


@supporters_bp.route('/login/musicbrainz/post')
@login_forbidden
def musicbrainz_post():
    """MusicBrainz OAuth2 callback endpoint."""
    if not musicbrainz_login.validate_post_login():
        raise BadRequest(gettext("Login failed!"))
    code = request.args.get('code')
    if not code:
        raise InternalServerError(gettext("Authorization code is missing!"))

    try:
        mb_username, mb_email = musicbrainz_login.get_supporter(code)
    except KeyError:
        raise BadRequest(gettext("Login failed!"))

    session.persist_data(**{
        SESSION_KEY_MB_USERNAME: mb_username,
        SESSION_KEY_MB_EMAIL: mb_email,
    })
    supporter = Supporter.get(musicbrainz_id=mb_username)
    if supporter:  # Checking if supporter is already signed up
        login_user(supporter)
        next = session.session.get('next')
        return redirect(next) if next else redirect(url_for('.profile'))
    else:
        flash.info("This is the first time you've signed into metabrainz.org, please sign up!")
        return redirect(url_for('.signup'))


@supporters_bp.route('/supporters/profile')
@login_required
def profile():
    return render_template("supporters/profile.html", current_supporter=current_user.supporter)


@supporters_bp.route('/supporters/profile/edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    if current_user.is_commercial:
        available_datasets = []
        form = CommercialSupporterEditForm()
    else:
        available_datasets = Dataset.query.all()
        form = NonCommercialSupporterEditForm(available_datasets)

    if form.validate_on_submit():
        kwargs = {
            "contact_name": form.contact_name.data,
            "contact_email": form.contact_email.data
        }

        if not current_user.is_commercial:
            kwargs["datasets"] = form.datasets.data

        current_user.supporter.update(**kwargs)
        flash.success("Profile updated.")
        return redirect(url_for('.profile'))
    else:
        form.contact_name.data = current_user.contact_name
        form.contact_email.data = current_user.contact_email

        if not current_user.is_commercial and current_user.datasets:
            form.datasets.data = [dataset.id for dataset in current_user.datasets]

    form_errors = {k: ". ".join(v) for k, v in form.errors.items()}
    form_data = dict(**form.data)
    form_data.pop("csrf_token", None)

    return render_template("supporters/profile-edit.html", props=json.dumps({
        "datasets": [{"id": d.id, "description": d.description, "name": d.name} for d in available_datasets],
        "is_commercial": current_user.is_commercial,
        "csrf_token": generate_csrf(),
        "initial_form_data": form_data,
        "initial_errors": form_errors
    }))


@supporters_bp.route('/supporters/profile/regenerate-token', methods=['POST'])
@login_required
def regenerate_token():
    try:
        return jsonify({'token': current_user.supporter.generate_token()})
    except InactiveSupporterException:
        raise BadRequest(gettext("Can't generate new token unless account is active."))
    except TokenGenerationLimitException as e:
        return jsonify({'error': e.message}), 429  # https://tools.ietf.org/html/rfc6585#page-3
