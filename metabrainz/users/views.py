from flask import Blueprint, request, redirect, render_template, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.exceptions import NotFound, InternalServerError, BadRequest
from metabrainz.model.tier import Tier
from metabrainz.model.user import User
from metabrainz.users import musicbrainz_login, login_forbidden
from metabrainz.users.forms import UserSignUpForm, CommercialSignUpForm
from metabrainz.users.notifications import send_user_signup_notification
from metabrainz import flash, session

users_bp = Blueprint('users', __name__)


@users_bp.route('/')
def index():
    return render_template('users/list.html', tiers=Tier.get_all())


@users_bp.route('/bad')
def bad_standing():
    return render_template('users/bad-standing.html')


@users_bp.route('/tiers/')
def tiers():
    return render_template('users/tiers.html', tiers=Tier.get_all())


@users_bp.route('/tiers/<tier_id>')
def tier(tier_id):
    t = Tier.get(tier_id)
    if t is None:
        raise NotFound("Can't find tier with a specified ID.")
    return render_template('users/tier.html', tier=t)


@users_bp.route('/signup/')
@login_forbidden
def signup():
    mb_username = session.fetch_data('mb_username')
    if mb_username:
        return render_template('users/signup-selection.html')
    else:
        return render_template('users/signup.html')


@users_bp.route('/signup/tier')
@login_forbidden
def signup_tier_selection():
    """Tier selection page for commercial users."""
    mb_username = session.fetch_data('mb_username')
    if mb_username:
        return render_template('users/signup-tier-selection.html', tiers=Tier.get_available())
    else:
        flash.warn("You need to sign in with your MusicBrainz account first!")
        return render_template('users/signup.html')


@users_bp.route('/signup/commercial/', methods=('GET', 'POST'))
@login_forbidden
def signup_commercial():
    """Sign up endpoint for commercial users.

    Commercial users need to choose support tier before filling out the form.
    `tier_id` argument with ID of a tier of choice is required there.
    """
    tier_id = request.args.get('tier_id')
    if not tier_id:
        flash.warn("You need to choose support tier before signing up!")
        return redirect(url_for('.signup_tier_selection'))
    tier = Tier.get(tier_id)
    if not tier:
        flash.error("You need to choose existing support tier before signing up!")
        return redirect(url_for(".signup_tier_selection"))
    if not tier.available:
        flash.error("You can't sign up for this tier on your own. Please "
                    "contact us if you want to do that.")
        return redirect(url_for('.tier', tier_id=tier_id))

    form = CommercialSignUpForm()
    if form.validate_on_submit():
        mb_username = session.fetch_data('mb_username')
        if not mb_username:
            flash.warn("You need to sign in with your MusicBrainz account first!")
            return render_template('users/signup.html')
        new_user = User.add(
            is_commercial=True,
            musicbrainz_id=mb_username,
            contact_name=form.contact_name.data,
            contact_email=form.contact_email.data,
            description=form.description.data,

            org_name=form.org_name.data,
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
        send_user_signup_notification(new_user)
        return render_template('users/signup-success.html')

    return render_template("users/signup-commercial.html", form=form, tier=tier)


@users_bp.route('/signup/non-commercial/', methods=('GET', 'POST'))
@login_forbidden
def signup_non_commercial():
    """Sign up endpoint for non-commercial users."""
    form = UserSignUpForm()
    if form.validate_on_submit():
        mb_username = session.fetch_data('mb_username')
        if not mb_username:
            flash.warn("You need to sign in with your MusicBrainz account first!")
            return render_template('users/signup.html')
        new_user = User.add(
            is_commercial=False,
            musicbrainz_id=mb_username,
            contact_name=form.contact_name.data,
            contact_email=form.contact_email.data,
            description=form.description.data,
        )
        login_user(new_user)
        return render_template('users/signup-success.html')

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
    mb_username = musicbrainz_login.get_user(code)
    session.persist_data(mb_username=mb_username)
    user = User.get(musicbrainz_id=mb_username)
    if user:  # Checking if user is already signed up
        login_user(user)
        next = session.session.get('next')
        return redirect(next) if next else redirect(url_for('users.profile'))
    else:
        return redirect(url_for('users.signup'))


@users_bp.route('/profile/')
@login_required
def profile():
    return render_template("users/profile.html")


@users_bp.route('/login/')
@login_forbidden
def login():
    return render_template('users/login.html')


@users_bp.route('/logout/')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('index.index'))
