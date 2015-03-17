from flask import Blueprint, jsonify, request, send_from_directory, current_app
from metabrainz.model.access_log import AccessLog
from metabrainz.api.decorators import require_token

api_bp = Blueprint('api', __name__)


@api_bp.route('/last')
@require_token
def last_replication_packet():
    """This endpoint returns number of the last available replication packet."""
    return jsonify({
        # TODO: Implement this:
        'last_packet': 0,
        'last_packet_daily': 0,
        'last_packet_weekly': 0,
    })


@api_bp.route('/replication/replication-<int:packet_number>.tar.bz2')
@require_token
def get_replication_packet(packet_number):
    response = send_from_directory(
        current_app.config['REPLICATION_PACKETS_DIR'],
        'replication-%s.tar.bz2' % packet_number,
        # explicitly specifying mimetype because detection is not working:
        mimetype='application/x-tar-bz2',
    )
    if response.status_code == 200:
        AccessLog.create_record(request.args.get('token'))
    return response


@api_bp.route('/replication/daily/replication-daily-<int:packet_number>.tar.bz2')
@require_token
def get_daily_replication_packet(packet_number):
    response = send_from_directory(
        current_app.config['REPLICATION_PACKETS_DAILY_DIR'],
        'replication-daily-%s.tar.bz2' % packet_number,
        # explicitly specifying mimetype because detection is not working:
        mimetype='application/x-tar-bz2',
    )
    if response.status_code == 200:
        AccessLog.create_record(request.args.get('token'))
    return response


@api_bp.route('/replication/weekly/replication-weekly-<int:packet_number>.tar.bz2')
@require_token
def get_weekly_replication_packet(packet_number):
    response = send_from_directory(
        current_app.config['REPLICATION_PACKETS_WEEKLY_DIR'],
        'replication-weekly-%s.tar.bz2' % packet_number,
        # explicitly specifying mimetype because detection is not working:
        mimetype='application/x-tar-bz2',
    )
    if response.status_code == 200:
        AccessLog.create_record(request.args.get('token'))
    return response
