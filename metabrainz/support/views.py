from flask import Blueprint, render_template
from metabrainz.model.tier import Tier

support_bp = Blueprint('support', __name__)


@support_bp.route('/')
def index():
    return render_template('support/index.html', tiers=Tier.get_all())
