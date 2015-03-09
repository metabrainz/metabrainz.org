from flask import Blueprint, jsonify, request, send_from_directory, current_app
from werkzeug.exceptions import BadRequest, Forbidden
from metabrainz.model.token import Token
from metabrainz.model.access_log import AccessLog

api_bp = Blueprint('api', __name__)


@api_bp.route('/last')
def last_replication_packet():
    """This endpoint returns number of the last available replication packet."""
    return jsonify({
        # TODO: Get number of the last available replication packet
        'last_packet': 0,
    })


@api_bp.route('/get/replication-<int:packet_number>.tar.bz2')
def get_replication_packet(packet_number):
    """This function provides a way to fetch replication packets.

    Access token is required to access replication packets
    """
    access_token = request.args.get('token')
    if not access_token:
        raise BadRequest("You need to provide an access token.")
    if not Token.is_valid(access_token):
        raise Forbidden("Provided access token is invalid.")

    resposnse = send_from_directory(
        current_app.config['REPLICATION_PACKETS_DIR'],
        'replication-%s.tar.bz2' % packet_number,
        # explicitly specifying mimetype because detection is not working:    )
        mimetype='application/x-tar-bz2',
    )

    if resposnse.status_code == 200:
        AccessLog.create_record(access_token, packet_number)

    return resposnse
