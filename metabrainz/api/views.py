from flask import Blueprint, jsonify, request, send_from_directory, current_app, render_template
from flask_login import login_required
from metabrainz.api.decorators import token_required, tracked

api_bp = Blueprint('api', __name__)


@api_bp.route('/')
@login_required
def info():
    """This view provides information about using the API."""
    return render_template('api/info.html')


@api_bp.route('/replication/info')
@token_required
def last_replication_packets():
    """This endpoint returns numbers of the last available replication packets."""
    return jsonify({
        # TODO: Implement this:
        'last_packet': 0,
        'last_packet_daily': 0,
        'last_packet_weekly': 0,
    })


@api_bp.route('/replication/replication-<int:packet_number>.tar.bz2')
@token_required
@tracked
def get_replication_packet(packet_number):
    response = send_from_directory(
        current_app.config['REPLICATION_PACKETS_DIR'],
        'replication-%s.tar.bz2' % packet_number,
        # explicitly specifying mimetype because detection is not working:
        mimetype='application/x-tar-bz2',
    )
    return response


@api_bp.route('/replication/daily/replication-daily-<int:packet_number>.tar.bz2')
@token_required
@tracked
def get_daily_replication_packet(packet_number):
    response = send_from_directory(
        current_app.config['REPLICATION_PACKETS_DAILY_DIR'],
        'replication-daily-%s.tar.bz2' % packet_number,
        # explicitly specifying mimetype because detection is not working:
        mimetype='application/x-tar-bz2',
    )
    return response


@api_bp.route('/replication/weekly/replication-weekly-<int:packet_number>.tar.bz2')
@token_required
@tracked
def get_weekly_replication_packet(packet_number):
    response = send_from_directory(
        current_app.config['REPLICATION_PACKETS_WEEKLY_DIR'],
        'replication-weekly-%s.tar.bz2' % packet_number,
        # explicitly specifying mimetype because detection is not working:
        mimetype='application/x-tar-bz2',
    )
    return response
