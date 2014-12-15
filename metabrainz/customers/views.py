from flask import Blueprint, render_template, flash, redirect, url_for
from werkzeug.exceptions import NotFound
from metabrainz.model.tier import Tier
from metabrainz.customers.forms import SignUpForm
from metabrainz.customers.notifications import send_org_signup_notification

customers_bp = Blueprint('customers', __name__)


@customers_bp.route('/')
def index():
    return render_template('customers/list.html', tiers=Tier.get_all())


@customers_bp.route('/tiers/')
def tiers():
    return render_template('customers/tiers.html', tiers=Tier.get_all())


@customers_bp.route('/tiers/<tier_id>')
def tier(tier_id):
    t = Tier.get_tier(tier_id)
    if t is None:
        raise NotFound("Can't find tier with a specified ID.")
    return render_template('customers/tier.html', tier=t)


@customers_bp.route('/tiers/<int:tier_id>/signup', methods=('GET', 'POST'))
def signup(tier_id):
    tier = Tier.get_tier(tier_id)
    if tier is None:
        flash('You need to select one of available tiers!', 'error')
        return redirect(url_for('.tiers'))

    if not tier.available:
        flash("You can't sign up for this tier on your own. Please contact us"
              "if you want to do that.", 'error')
        return redirect(url_for('.tier', tier_id=tier_id))

    form = SignUpForm()

    if form.validate_on_submit():
        send_org_signup_notification([
            ('Organization name', form.org_name.data),
            ('Contact name', form.contact_name.data),
            ('Contact email', form.contact_email.data),

            ('Website URL', form.website_url.data),
            ('Logo image URL', form.logo_url.data),
            ('API URL', form.api_url.data),

            ('Street', form.address_street.data),
            ('City', form.address_city.data),
            ('State', form.address_state.data),
            ('Postal code', form.address_postcode.data),
            ('Country', form.address_country.data),

            ('Tier', '#%s - %s' % (tier.id, tier.name)),
            ('Payment method', form.payment_method.data),

            ('Usage description', form.description.data),
        ])
        return render_template('customers/signup-success.html')

    else:
        return render_template('customers/signup.html', form=form, tier=tier)


@customers_bp.route('/bad')
def bad_standing():
    return render_template('customers/bad-standing.html')
