from flask import Blueprint, render_template, request, flash, redirect, url_for
from metabrainz.model.tier import Tier
from werkzeug.exceptions import NotFound
from metabrainz.support.forms import SignUpForm
from metabrainz.support.notifications import send_org_signup_notification

support_bp = Blueprint('support', __name__)


@support_bp.route('/tiers')
def index():
    return render_template('support/index.html', tiers=Tier.get_all())


@support_bp.route('/signup', methods=('GET', 'POST'))
def signup():
    tier_id = request.args.get('tier_id')
    if tier_id is None:
        flash('You need to select one of the tiers first!', 'error')
        return redirect(url_for('.index'))

    try:
        tier = Tier.get_tier(int(tier_id))
    except ValueError:
        tier = None
    if tier is None:
        flash('You need to select one of available tiers!', 'error')
        return redirect(url_for('.index'))

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
        return render_template('support/signup-success.html')

    else:
        return render_template('support/signup.html', form=form, tier=tier)


@support_bp.route('/tiers/<tier_id>')
def tier(tier_id):
    t = Tier.get_tier(tier_id)
    if t is None:
        raise NotFound("Can't find tier with a specified ID.")
    return render_template('support/tier.html', tier=t)


@support_bp.route('/bad')
def bad_standing():
    return render_template('support/bad-standing.html')
