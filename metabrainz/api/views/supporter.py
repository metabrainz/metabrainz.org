from flask import Blueprint, jsonify
from metabrainz.oauth import oauth_provider
from metabrainz.model.supporter import Supporter

api_supporter_bp = Blueprint('api_supporter', __name__)


@api_supporter_bp.route('/')
@oauth_provider.require_auth()
def supporter(supporter_id):
    supporter = Supporter.get(id=supporter_id)
    return jsonify({
        "username": supporter.musicbrainz_id,
    })
