from flask import Blueprint, request, redirect, render_template, url_for, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.exceptions import NotFound, InternalServerError, BadRequest
from metabrainz.model.tier import Tier
from metabrainz.model.user import User, InactiveUserException
from metabrainz.model.token import TokenGenerationLimitException
from metabrainz.users import musicbrainz_login, login_forbidden
from metabrainz.users.forms import CommercialSignUpForm, NonCommercialSignUpForm, UserEditForm
from metabrainz import flash, session

users_bp = Blueprint('users', __name__)

SESSION_KEY_ACCOUNT_TYPE = 'account_type'
SESSION_KEY_TIER_ID = 'account_tier'
SESSION_KEY_MB_USERNAME = 'mb_username'
SESSION_KEY_MB_EMAIL = 'mb_email'

ACCOUNT_TYPE_COMMERCIAL = 'commercial'
ACCOUNT_TYPE_NONCOMMERCIAL = 'noncommercial'


@users_bp.route('/supporters')
def supporters_list():
    return render_template('users/supporters-list.html', tiers=Tier.get_available(sort=True, sort_desc=True))


@users_bp.route('/supporters/bad')
def bad_standing():
    return render_template('users/bad-standing.html')


@users_bp.route('/supporters/account-type')
def account_type():
    return render_template('users/account-type.html', tiers=Tier.get_available(sort=True))


@users_bp.route('/supporters/tiers/<tier_id>')
def tier(tier_id):
    t = Tier.get(id=tier_id)
    if not t or not t.available:
        raise NotFound("Can't find tier with a specified ID.")
    return render_template('users/tier.html', tier=t)


@users_bp.route('/signup')
@login_forbidden
def signup():
    mb_username = session.fetch_data(SESSION_KEY_MB_USERNAME)
    if mb_username is None:
        # Show template with a link to MusicBrainz OAuth page
        return render_template('users/mb-signup.html')

    account_type = session.fetch_data(SESSION_KEY_ACCOUNT_TYPE)
    if not account_type:
        flash.info("Please select account type to sign up.")
        return redirect(url_for(".account_type"))

    if account_type == ACCOUNT_TYPE_COMMERCIAL:
        tier_id = session.fetch_data(SESSION_KEY_TIER_ID)
        if not tier_id:
            flash.info("Please select account type to sign up.")
            return redirect(url_for(".account_type"))
        return redirect(url_for(".signup_commercial", tier_id=tier_id))
    else:
        return redirect(url_for(".signup_noncommercial"))


@users_bp.route('/signup/commercial', methods=('GET', 'POST'))
@login_forbidden
def signup_commercial():
    """Sign up endpoint for commercial users.

    Commercial users need to choose support tier before filling out the form.
    `tier_id` argument with ID of a tier of choice is required there.
    """
    tier_id = request.args.get('tier_id')
    if not tier_id:
        flash.warn("You need to choose support tier before signing up!")
        return redirect(url_for('.account_type'))
    selected_tier = Tier.get(id=tier_id)
    if not selected_tier or not selected_tier.available:
        flash.error("You need to choose existing tier before signing up!")
        return redirect(url_for(".account_type"))

    mb_username = session.fetch_data(SESSION_KEY_MB_USERNAME)
    if not mb_username:
        session.persist_data(**{
            SESSION_KEY_ACCOUNT_TYPE: ACCOUNT_TYPE_COMMERCIAL,
            SESSION_KEY_TIER_ID: selected_tier.id,
        })
        return redirect(url_for(".signup"))
    mb_email = session.fetch_data(SESSION_KEY_MB_EMAIL)

    form = CommercialSignUpForm(default_email=mb_email)
    if form.validate_on_submit():
        new_user = User.add(
            is_commercial=True,
            musicbrainz_id=mb_username,
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
            payment_method=form.payment_method.data,
        )
        login_user(new_user)
        flash.success("Thanks for signing up! Your application will be reviewed soon.")
        return redirect(url_for('.profile'))

    return render_template("users/signup-commercial.html", form=form, tier=selected_tier)


@users_bp.route('/signup/noncommercial', methods=('GET', 'POST'))
@login_forbidden
def signup_noncommercial():
    """Sign up endpoint for non-commercial users."""
    mb_username = session.fetch_data(SESSION_KEY_MB_USERNAME)
    if not mb_username:
        session.persist_data(**{
            SESSION_KEY_ACCOUNT_TYPE: ACCOUNT_TYPE_NONCOMMERCIAL,
        })
        return redirect(url_for(".signup"))
    mb_email = session.fetch_data(SESSION_KEY_MB_EMAIL)

    form = NonCommercialSignUpForm(default_email=mb_email)
    if form.validate_on_submit():
        new_user = User.add(
            is_commercial=False,
            musicbrainz_id=mb_username,
            contact_name=form.contact_name.data,
            contact_email=form.contact_email.data,
            data_usage_desc=form.usage_desc.data,
        )
        login_user(new_user)
        flash.success("Thanks for signing up!")
        return redirect(url_for('.profile'))

    return render_template("users/signup-non-commercial.html", form=form)


@users_bp.route('/login/musicbrainz')
@login_forbidden
def musicbrainz():
    session.session['next'] = request.args.get('next')
    return redirect(musicbrainz_login.get_authentication_uri())


@users_bp.route('/login/musicbrainz/post')
@login_forbidden
def musicbrainz_post():
    """MusicBrainz OAuth2 callback endpoint."""
    if not musicbrainz_login.validate_post_login():
        raise BadRequest("Login failed!")
    code = request.args.get('code')
    if not code:
        raise InternalServerError("Authorization code is missing!")
    mb_username, mb_email = musicbrainz_login.get_user(code)
    session.persist_data(**{
        SESSION_KEY_MB_USERNAME: mb_username,
        SESSION_KEY_MB_EMAIL: mb_email,
    })
    user = User.get(musicbrainz_id=mb_username)
    if user:  # Checking if user is already signed up
        login_user(user)
        next = session.session.get('next')
        return redirect(next) if next else redirect(url_for('.profile'))
    else:
        return redirect(url_for('.signup'))


@users_bp.route('/profile')
@login_required
def profile():
    return render_template("users/profile.html")


@users_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    form = UserEditForm()
    if form.validate_on_submit():
        current_user.update(
            contact_name=form.contact_name.data,
            contact_email=form.contact_email.data,
        )
        flash.success("Profile updated.")
        return redirect(url_for('.profile'))
    else:
        form.contact_name.data = current_user.contact_name
        form.contact_email.data = current_user.contact_email
    return render_template('users/profile-edit.html', form=form)


@users_bp.route('/profile/regenerate-token', methods=['POST'])
@login_required
def regenerate_token():
    try:
        return jsonify({'token': current_user.generate_token()})
    except InactiveUserException:
        raise BadRequest("Can't generate new token unless account is active.")
    except TokenGenerationLimitException as e:
        return jsonify({'error': e.message}), 429  # https://tools.ietf.org/html/rfc6585#page-3


@users_bp.route('/login')
@login_forbidden
def login():
    return render_template('users/mb-login.html')


@users_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('index.home'))
