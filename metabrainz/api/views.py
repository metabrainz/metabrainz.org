from flask import Blueprint, jsonify, request
from werkzeug.exceptions import BadRequest, Forbidden
from metabrainz.model.token import Token

api_bp = Blueprint('api', __name__)


@api_bp.route('/last')
def last_replication_packet():
    """This endpoint returns number of the last available replication packet."""
    return jsonify({
        # TODO: Get number of the last available replication packet
        'last_packet': 0,
    })


@api_bp.route('/get/<int:packet_number>')
def get_replication_packet(packet_number):
    """This function provides a way to fetch replication packets.

    Access token is required to access replication packets
    """
    access_token = request.args.get('token')
    if not access_token:
        raise BadRequest("You need to provide access token.")
    if not Token.is_valid(access_token):
        raise Forbidden("Provided access token is invalid.")

    # TODO: Check if packet is there, fetch it, and log this request in a DB.
    raise NotImplementedError
