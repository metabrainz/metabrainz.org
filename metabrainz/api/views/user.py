from flask import Blueprint, jsonify
from metabrainz.oauth import oauth_provider
from metabrainz.model.user import User

api_user_bp = Blueprint('api_user', __name__)


@api_user_bp.route('/')
@oauth_provider.require_auth()
def user(user_id):
    user = User.get(id=user_id)
    return jsonify({
        "username": user.musicbrainz_id,
    })
