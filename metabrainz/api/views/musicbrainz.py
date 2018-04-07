from flask import Blueprint, jsonify, send_from_directory, current_app
from flask.helpers import safe_join
from werkzeug.wrappers import Response
from werkzeug.urls import iri_to_uri
from metabrainz.api.decorators import token_required, tracked
import logging
import time
import re
import os

api_musicbrainz_bp = Blueprint('api_musicbrainz', __name__)

NGINX_INTERNAL_LOCATION = '/internal/replication'

MIMETYPE_ARCHIVE_BZ2 = 'application/x-tar-bz2'
MIMETYPE_ARCHIVE_XZ = 'application/x-xz'
MIMETYPE_SIGNATURE = 'text/plain'

# These durations are used to create nagios compatible status codes so we can monitor
# the replication packet stream.
MAX_PACKET_AGE_WARNING = 60 * 60 * 2  # 4 hours
MAX_PACKET_AGE_CRITICAL = 60 * 60 * 6  # 4 hours


@api_musicbrainz_bp.route('/replication-check')
def replication_check():
    """Check that all the replication packets are contiguous and that no packet
    is more than a few hours old. Output a Nagios compatible line of text.
    """

    try:
        entries = [os.path.join(current_app.config['REPLICATION_PACKETS_DIR'], e)
                   for e in os.listdir(current_app.config['REPLICATION_PACKETS_DIR'])]
    except OSError as e:
        logging.warning(e)
        return Response("UNKNOWN " + str(e), mimetype='text/plain')

    pattern = re.compile("replication-[0-9]+.tar.bz2$")
    entries = filter(lambda x: pattern.search(x), entries)
    entries = filter(os.path.isfile, entries)
    entries = _sort_natural(entries)

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
            resp = "CRITICAL Replication packet %d is missing" % (num - 1)
        last = num

    if resp != "OK":
        return Response(resp, mimetype='text/plain')
        
    last_packet_age = time.time() - os.path.getmtime(entries[-1]) 
    if last_packet_age > MAX_PACKET_AGE_CRITICAL:
        resp = "CRITICAL Latest replication packet is %.1f hours old" % (last_packet_age / 3600)
    elif last_packet_age > MAX_PACKET_AGE_WARNING:
        resp = "WARNING Latest replication packet is %.1f hours old" % (last_packet_age / 3600)

    return Response(resp, mimetype='text/plain')


@api_musicbrainz_bp.route('/replication-info')
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
        entries = _sort_natural(entries, reverse=True)  # latest first
        return os.path.split(entries[0])[-1] if entries else None

    # TODO(roman): Cache this response:
    return jsonify({
        'last_packet': _get_last_packet_name(
            current_app.config['REPLICATION_PACKETS_DIR'],
            "replication-[0-9]+.tar.bz2$"
        ),
    })


@api_musicbrainz_bp.route('/replication-<int:packet_number>.tar.bz2')
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
        return send_from_directory(directory, filename, mimetype=MIMETYPE_ARCHIVE_BZ2)


@api_musicbrainz_bp.route('/replication-<int:packet_number>.tar.bz2.asc')
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


@api_musicbrainz_bp.route('/json-dumps/json-dump-<int:packet_number>/<entity_name>.tar.xz')
@token_required
@tracked
def json_dump(packet_number, entity_name):
    """Endpoint that provides access to the JSON dump files.

    See MEB-93 for more info.
    """
    directory = os.path.join(current_app.config['JSON_DUMPS_DIR'], "json-dump-%s" % packet_number)
    filename = '%s.tar.xz' % entity_name
    if not os.path.isfile(safe_join(directory, filename)):
        return Response("Can't find specified JSON dump!", status=404)
    return send_from_directory(directory, filename, mimetype=MIMETYPE_ARCHIVE_XZ)


def _redirect_to_nginx(location):
    """This creates an internal redirection to a specified location.

    This feature is only supported by nginx. See http://wiki.nginx.org/X-accel
    for more information about it.
    """
    response = Response(status=200)
    location = iri_to_uri(location, safe_conversion=True)
    response.headers['X-Accel-Redirect'] = location
    return response


def _sort_natural(names_list, reverse=False):
    """Sort list using a natural sort order.

    https://en.wikipedia.org/wiki/Natural_sort_order
    """
    def sort_key(val):
        return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', val)]

    return sorted(names_list, key=sort_key, reverse=reverse)
