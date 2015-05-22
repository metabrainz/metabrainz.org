from flask import Blueprint, jsonify, send_from_directory, current_app, render_template
from flask.helpers import safe_join
from werkzeug.wrappers import Response
from werkzeug.urls import iri_to_uri
from metabrainz.api.decorators import token_required, tracked
import logging
import re
import os
import time

api_bp = Blueprint('api', __name__)

NGINX_INTERNAL_LOCATION = '/internal/replication'

MIMETYPE_ARCHIVE = 'application/x-tar-bz2'
MIMETYPE_SIGNATURE = 'text/plain'

DAILY_SUBDIR = 'daily'
WEEKLY_SUBDIR = 'weekly'

# These durations are used to create nagios compatible status codes so we can monitor
# the replication packet stream.
MAX_PACKET_AGE_WARNING = 60 * 60 * 2 # 4 hours
MAX_PACKET_AGE_CRITICAL = 60 * 60 * 6 # 4 hours

@api_bp.route('/')
def info():
    """This view provides information about using the API."""
    return render_template('api/info.html')

@api_bp.route('/musicbrainz/replication-check')
def replication_check():
    """Check that all the replication packets are contiguous and that no packet is more than a 
       few hours old. Output a Nagios compatible line of text."""

    try:
        entries = [os.path.join(current_app.config['REPLICATION_PACKETS_DIR'], e) 
                     for e in os.listdir(current_app.config['REPLICATION_PACKETS_DIR'])]
    except OSError as e:
        logging.warning(e)
        return Response("UNKNOWN " + str(e), mimetype='text/plain')

    pattern = re.compile("replication-[0-9]+.tar.bz2$")
    entries = filter(lambda x: pattern.search(x), entries)
    entries = filter(os.path.isfile, entries)
    entries.sort()

    if len(entries) == 0:
        return Response("UNKNOWN no replication packets available", mimetype='text/plain')

    resp = "OK"
    last = -1
    pattern = re.compile("replication-([0-9]+).tar.bz2$")
    for entry in entries:
        m = pattern.search(entry)
        if not m:
            resp = "UNKNOWN Unkown files in the replication directory"
            break
        num = int(m.groups()[0])
        if last < 0:
            last = num - 1

        if last != num - 1:
            resp = "CRITICAL Replication packet %d is missing" % (num -1)

        last = num

    if resp != "OK":
        return Response(resp, mimetype='text/plain')
        
    last_packet_age = time.time() - os.path.getmtime(entries[-1]) 
    if last_packet_age > MAX_PACKET_AGE_CRITICAL:
        resp = "CRITICAL Latest replication packet is %.1f hours old" % (last_packet_age / 3600)
    elif last_packet_age > MAX_PACKET_AGE_WARNING:
        resp = "WARNING Latest replication packet is %.1f hours old" % (last_packet_age / 3600)

    return Response(resp, mimetype='text/plain')


@api_bp.route('/musicbrainz/replication-info')
@token_required
def replication_info():
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
            "replication-[0-9]+.tar.bz2$"
        ),
        'last_packet_daily': _get_last_packet_name(
            os.path.join(current_app.config['REPLICATION_PACKETS_DIR'], DAILY_SUBDIR),
            "replication-daily-[0-9]+.tar.bz2$"
        ),
        'last_packet_weekly': _get_last_packet_name(
            os.path.join(current_app.config['REPLICATION_PACKETS_DIR'], WEEKLY_SUBDIR),
            "replication-weekly-[0-9]+.tar.bz2$"
        ),
    })

@api_bp.route('/musicbrainz/replication-<int:packet_number>.tar.bz2')
@token_required
@tracked
def replication_hourly(packet_number):
    directory = current_app.config['REPLICATION_PACKETS_DIR']
    filename = 'replication-%s.tar.bz2' % packet_number
    if not os.path.isfile(safe_join(directory, filename)):
        return Response("Can't find specified replication packet!\n", status=404)

    if 'USE_NGINX_X_ACCEL' in current_app.config and current_app.config['USE_NGINX_X_ACCEL']:
        return _redirect_to_nginx(os.path.join(NGINX_INTERNAL_LOCATION, filename))
    else:
        return send_from_directory(directory, filename, mimetype=MIMETYPE_ARCHIVE)


@api_bp.route('/musicbrainz/replication-<int:packet_number>.tar.bz2.asc')
@token_required
def replication_hourly_signature(packet_number):
    directory = current_app.config['REPLICATION_PACKETS_DIR']
    filename = 'replication-%s.tar.bz2.asc' % packet_number
    if not os.path.isfile(safe_join(directory, filename)):
        return Response("Can't find signature for a specified replication packet!\n", status=404)

    if 'USE_NGINX_X_ACCEL' in current_app.config and current_app.config['USE_NGINX_X_ACCEL']:
        return _redirect_to_nginx(os.path.join(NGINX_INTERNAL_LOCATION, filename))
    else:
        return send_from_directory(directory, filename, mimetype=MIMETYPE_SIGNATURE)


@api_bp.route('/musicbrainz/replication-daily-<int:packet_number>.tar.bz2')
@token_required
@tracked
def replication_daily(packet_number):
    directory = os.path.join(current_app.config['REPLICATION_PACKETS_DIR'], DAILY_SUBDIR)
    filename = 'replication-daily-%s.tar.bz2' % packet_number
    if not os.path.isfile(safe_join(directory, filename)):
        return Response("Can't find specified replication packet!\n", status=404)

    if 'USE_NGINX_X_ACCEL' in current_app.config and current_app.config['USE_NGINX_X_ACCEL']:
        return _redirect_to_nginx(os.path.join(NGINX_INTERNAL_LOCATION, DAILY_SUBDIR, filename))
    else:
        return send_from_directory(directory, filename, mimetype=MIMETYPE_ARCHIVE)


@api_bp.route('/musicbrainz/replication-daily-<int:packet_number>.tar.bz2.asc')
@token_required
def replication_daily_signature(packet_number):
    directory = os.path.join(current_app.config['REPLICATION_PACKETS_DIR'], DAILY_SUBDIR)
    filename = 'replication-daily-%s.tar.bz2.asc' % packet_number
    if not os.path.isfile(safe_join(directory, filename)):
        return Response("Can't find signature for a specified replication packet!\n", status=404)

    if 'USE_NGINX_X_ACCEL' in current_app.config and current_app.config['USE_NGINX_X_ACCEL']:
        return _redirect_to_nginx(os.path.join(NGINX_INTERNAL_LOCATION, DAILY_SUBDIR, filename))
    else:
        return send_from_directory(directory, filename, mimetype=MIMETYPE_SIGNATURE)


@api_bp.route('/musicbrainz/replication-weekly-<int:packet_number>.tar.bz2')
@token_required
@tracked
def replication_weekly(packet_number):
    directory = os.path.join(current_app.config['REPLICATION_PACKETS_DIR'], WEEKLY_SUBDIR)
    filename = 'replication-weekly-%s.tar.bz2' % packet_number
    if not os.path.isfile(safe_join(directory, filename)):
        return Response("Can't find specified replication packet!\n", status=404)

    if 'USE_NGINX_X_ACCEL' in current_app.config and current_app.config['USE_NGINX_X_ACCEL']:
        return _redirect_to_nginx(os.path.join(NGINX_INTERNAL_LOCATION, WEEKLY_SUBDIR, filename))
    else:
        return send_from_directory(directory, filename, mimetype=MIMETYPE_ARCHIVE)


@api_bp.route('/musicbrainz/replication-weekly-<int:packet_number>.tar.bz2.asc')
@token_required
def replication_weekly_signature(packet_number):
    directory = os.path.join(current_app.config['REPLICATION_PACKETS_DIR'], WEEKLY_SUBDIR)
    filename = 'replication-weekly-%s.tar.bz2.asc' % packet_number
    if not os.path.isfile(safe_join(directory, filename)):
        return Response("Can't find signature for a specified replication packet!\n", status=404)

    if 'USE_NGINX_X_ACCEL' in current_app.config and current_app.config['USE_NGINX_X_ACCEL']:
        return _redirect_to_nginx(os.path.join(NGINX_INTERNAL_LOCATION, WEEKLY_SUBDIR, filename))
    else:
        return send_from_directory(directory, filename, mimetype=MIMETYPE_SIGNATURE)


def _redirect_to_nginx(location):
    """This creates an internal redirection to a specified location.

    This feature is only supported by nginx. See http://wiki.nginx.org/X-accel
    for more information about it.
    """
    response = Response(status=200)
    location = iri_to_uri(location, safe_conversion=True)
    response.headers['X-Accel-Redirect'] = location
    return response
