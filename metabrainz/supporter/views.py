import json

from flask import Blueprint, request, redirect, render_template, url_for, jsonify, current_app
from flask_babel import gettext
from flask_login import login_user, login_required, current_user
from flask_wtf.csrf import generate_csrf
from werkzeug.exceptions import NotFound, BadRequest

from metabrainz import flash
from metabrainz.model import Dataset, db
from metabrainz.model.supporter import Supporter, InactiveSupporterException
from metabrainz.model.tier import Tier
from metabrainz.model.token import TokenGenerationLimitException
from metabrainz.model.user import User
from metabrainz.model.webhook import EVENT_USER_CREATED
from metabrainz.supporter.forms import CommercialSignUpForm, NonCommercialSignUpForm, CommercialUpgradeForm, NonCommercialUpgradeForm
from metabrainz.user.email import send_verification_email
from metabrainz.user.rate_limit import check_signup_rate_limit, increment_signup_count

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
    """Account type selection page for new supporters."""
    existing_user = current_user.is_authenticated
    if existing_user and current_user.supporter:
        flash.info(gettext("You are already a supporter."))
        return redirect(url_for('index.profile'))

    return render_template(
        'supporters/account-type.html',
        tiers=Tier.get_available(sort=True),
        featured_supporters=Supporter.get_featured(),
        existing_user=existing_user,
    )


@supporters_bp.route('/supporters/tiers/<int:tier_id>')
def tier(tier_id):
    t = Tier.get(id=tier_id)
    if not t or not t.available:
        raise NotFound(gettext("Can't find tier with a specified ID."))
    return render_template('supporters/tier.html', tier=t)


def _create_commercial_supporter(form, tier_id, user):
    """Create a commercial supporter record."""
    Supporter.add(
        is_commercial=True,
        contact_name=form.contact_name.data,
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
        amount_pledged=float(form.amount_pledged.data),
        datasets=[],
        user=user
    )


def _create_noncommercial_supporter(form, user):
    """Create a non-commercial supporter record."""
    Supporter.add(
        is_commercial=False,
        contact_name=form.contact_name.data,
        data_usage_desc=form.usage_desc.data,
        datasets=form.datasets.data,
        user=user
    )


def _check_user_exists(form):
    """Check if username or email already exists. Returns error field name or None."""
    user = User.get(name=form.username.data)
    if user is not None:
        form.username.errors.append(f"Another user with username '{form.username.data}' exists.")
        return "username"

    user = User.get(email=form.email.data)
    if user is not None:
        form.email.errors.append(f"Another user with email '{form.email.data}' exists.")
        return "email"

    return None


@supporters_bp.route('/signup/commercial', methods=('GET', 'POST'))
def signup_commercial():
    """Sign up endpoint for commercial supporters (new users and existing users)."""
    existing_user = bool(current_user.is_authenticated)
    if existing_user and current_user.supporter:
        flash.info(gettext("You are already a supporter."))
        return redirect(url_for('index.profile'))

    csrf_token = generate_csrf()
    mtcaptcha_site_key = current_app.config.get("MTCAPTCHA_PUBLIC_KEY")

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
    _tier = {
        "name": selected_tier.name,
        "price": float(selected_tier.price)
    }

    # Use different form based on whether user is logged in
    if existing_user:
        form = CommercialUpgradeForm(selected_tier)
        form_data = dict(**form.data)
        if not form_data.get("contact_name"):
            form_data["contact_name"] = current_user.name
    else:
        form = CommercialSignUpForm(selected_tier)
        form_data = dict(**form.data)
    if form_data["amount_pledged"]:
        form_data["amount_pledged"] = float(form_data["amount_pledged"])
    form_data.pop("csrf_token", None)

    if form.validate_on_submit():
        if existing_user:
            # Existing user becoming a supporter
            _create_commercial_supporter(form, tier_id, current_user)
            db.session.commit()

            flash.success(gettext(
                "Thanks for becoming a supporter! Your application will be reviewed "
                "soon. We will send you updates via email."
            ))
            return redirect(url_for('index.profile'))
        else:
            # New user signup
            if check_signup_rate_limit(form) or _check_user_exists(form):
                return render_template("supporters/signup-commercial.html", props=json.dumps({
                    "tier": _tier,
                    "mtcaptcha_site_key": mtcaptcha_site_key,
                    "csrf_token": csrf_token,
                    "initial_form_data": form_data,
                    "initial_errors": form.props_errors,
                    "existing_user": False
                }))

            user = User.add(name=form.username.data, unconfirmed_email=form.email.data, password=form.password.data)
            _create_commercial_supporter(form, tier_id, user)
            db.session.commit()
            increment_signup_count()

            user.emit_event(EVENT_USER_CREATED)
            flash.success(gettext(
                "Thanks for signing up! Your application will be reviewed "
                "soon. We will send you updates via email."
            ))
            send_verification_email(
                user,
                "[MetaBrainz] Sign up confirmation",
                "email/supporter-commercial-welcome-email-address-verification.txt"
            )
            login_user(user)
            return redirect(url_for('index.profile'))

    props = {
        "tier": _tier,
        "mtcaptcha_site_key": mtcaptcha_site_key,
        "csrf_token": csrf_token,
        "initial_form_data": form_data,
        "initial_errors": form.props_errors,
        "existing_user": existing_user
    }
    if existing_user:
        props["user"] = {
            "username": current_user.name,
            "email": current_user.get_email_any()
        }

    return render_template("supporters/signup-commercial.html", props=json.dumps(props))


@supporters_bp.route('/signup/noncommercial', methods=('GET', 'POST'))
def signup_noncommercial():
    """Sign up endpoint for non-commercial supporters (new users and existing users)."""
    existing_user = bool(current_user.is_authenticated)
    if existing_user and current_user.supporter:
        flash.info(gettext("You are already a supporter."))
        return redirect(url_for('index.profile'))

    available_datasets = Dataset.query.all()
    dataset_dicts = [
        {"id": d.id, "description": d.description, "name": d.name}
        for d in available_datasets
    ]
    csrf_token = generate_csrf()
    mtcaptcha_site_key = current_app.config.get("MTCAPTCHA_PUBLIC_KEY")

    if existing_user:
        form = NonCommercialUpgradeForm(available_datasets)
        form_data = dict(**form.data)
        if not form_data.get("contact_name"):
            form_data["contact_name"] = current_user.name
    else:
        form = NonCommercialSignUpForm(available_datasets)
        form_data = dict(**form.data)

    form_data.pop("csrf_token", None)

    if form.validate_on_submit():
        if existing_user:
            # Existing user becoming a supporter
            _create_noncommercial_supporter(form, current_user)
            db.session.commit()

            flash.success(gettext("Thanks for becoming a supporter!"))
            return redirect(url_for('index.profile'))
        else:
            # New user signup
            if check_signup_rate_limit(form) or _check_user_exists(form):
                return render_template("supporters/signup-non-commercial.html", props=json.dumps({
                    "datasets": dataset_dicts,
                    "mtcaptcha_site_key": mtcaptcha_site_key,
                    "csrf_token": csrf_token,
                    "initial_form_data": form_data,
                    "initial_errors": form.props_errors,
                    "existing_user": False
                }))

            user = User.add(name=form.username.data, unconfirmed_email=form.email.data, password=form.password.data)
            _create_noncommercial_supporter(form, user)
            db.session.commit()
            increment_signup_count()

            user.emit_event(EVENT_USER_CREATED)
            send_verification_email(
                user,
                "[MetaBrainz] Sign up confirmation",
                "email/supporter-noncommercial-welcome-email-address-verification.txt"
            )

            flash.success(gettext("Thanks for signing up! Please check your inbox to complete verification."))

            login_user(user)
            return redirect(url_for('index.profile'))

    props = {
        "datasets": dataset_dicts,
        "mtcaptcha_site_key": mtcaptcha_site_key,
        "csrf_token": csrf_token,
        "initial_form_data": form_data,
        "initial_errors": form.props_errors,
        "existing_user": existing_user,
    }
    if existing_user:
        props["user"] = {
            "username": current_user.name,
            "email": current_user.get_email_any()
        }

    return render_template("supporters/signup-non-commercial.html", props=json.dumps(props))


@supporters_bp.route('/supporters/profile/regenerate-token', methods=['POST'])
@login_required
def regenerate_token():
    try:
        return jsonify({'token': current_user.supporter.generate_token()})
    except InactiveSupporterException:
        raise BadRequest(gettext("Can't generate new token unless account is active."))
    except TokenGenerationLimitException as e:
        return jsonify({'error': e.args[0]}), 429  # https://tools.ietf.org/html/rfc6585#page-3
