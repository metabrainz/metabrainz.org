from flask import Blueprint, jsonify, send_from_directory, current_app, render_template
from metabrainz.api.decorators import token_required, tracked
import logging
import re
import os

api_bp = Blueprint('api', __name__)


@api_bp.route('/')
def info():
    """This view provides information about using the API."""
    return render_template('api/info.html')


@api_bp.route('/musicbrainz/replication/info')
@token_required
def last_replication_packets():
    """This endpoint returns numbers of the last available replication packets."""

    def _get_last_packet_name(location, pattern):
        try:
            entries = [os.path.join(location, e) for e in os.listdir(location)]
        except OSError as e:
            logging.warning(e)
            return None
        pattern = re.compile(pattern)
        entries = filter(lambda x: pattern.search(x), entries)
        entries = filter(os.path.isfile, entries)
        entries.sort(reverse=True)  # latest first
        return os.path.split(entries[0])[-1] if entries else None

    # TODO(roman): Cache this response:
    return jsonify({
        'last_packet': _get_last_packet_name(
            current_app.config['REPLICATION_PACKETS_DIR'],
            "replication-[0-9]+.tar.bz2"
        ),
        'last_packet_daily': _get_last_packet_name(
            current_app.config['REPLICATION_PACKETS_DAILY_DIR'],
            "replication-daily-[0-9]+.tar.bz2"
        ),
        'last_packet_weekly': _get_last_packet_name(
            current_app.config['REPLICATION_PACKETS_WEEKLY_DIR'],
            "replication-weekly-[0-9]+.tar.bz2"
        ),
    })


@api_bp.route('/musicbrainz/replication/replication-<int:packet_number>.tar.bz2')
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


@api_bp.route('/musicbrainz/replication/daily/replication-daily-<int:packet_number>.tar.bz2')
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


@api_bp.route('/musicbrainz/replication/weekly/replication-weekly-<int:packet_number>.tar.bz2')
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
