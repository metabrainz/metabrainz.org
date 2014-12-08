from flask import Blueprint, render_template, request, flash, redirect, url_for
from metabrainz.model.tier import Tier
from werkzeug.exceptions import NotFound
from metabrainz.support.forms import SignUpForm

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

    tier = Tier.get_tier(tier_id)
    if not tier.available:
        flash("You can't sign up for this tier on your own. Please contact us"
              "if you want to do that.", 'error')
        return redirect(url_for('.tier', tier_id=tier_id))

    form = SignUpForm()

    if form.validate_on_submit():
        # TODO: Send email notification to admin
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
