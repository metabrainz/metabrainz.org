from flask import Blueprint, render_template
from metabrainz.model.tier import Tier
from werkzeug.exceptions import NotFound

support_bp = Blueprint('support', __name__)


@support_bp.route('/tiers')
def index():
    return render_template('support/index.html', tiers=Tier.get_all())


@support_bp.route('/tiers/<tier_id>')
def tier(tier_id):
    t = Tier.get_tier(tier_id)
    if t is None:
        raise NotFound("Can't find tier with a specified ID.")
    return render_template('support/tier.html', tier=t)
