from flask import Blueprint, g, request, Response, jsonify
from metabrainz.api.decorators import token_required
from datetime import datetime, timezone
from metabrainz.model.notification import NotificationProjectType
from metabrainz.db.notification import fetch_notifications, validate_notification_ids_for_user, mark_read_unread, delete_notifications


DEFAULT_NOTIFICATION_FETCH_COUNT = 100
notification_bp = Blueprint("notification", __name__)


@notification_bp.get("/fetch")
@token_required
def get_notifications():
    """
    Fetch notifications for a user.
    An access token (available on https://metabrainz.org/profile) must be provided in the Authorization header.
    
    If none of the optional parameters are specified, this endpoint returns the 
    :data:`~DEFAULT_NOTIFICATION_FETCH_COUNT` most recent notifications across all projects, including both read and unread.

    Returns a JSON array of dicts containing notifications for the user with specified parameters. Example:

    .. code-block:: json

        [
            {
                "body": "The voices are getting louder.",
                "id": 13,
                "important": false,
                "project": "listenbrainz",
                "read": false,
                "sent_at": "Mon, 26 May 2025 17:55:50 GMT",
                "user_id": 1
            }
        ]

    :reqheader Authorization: Token <access token>
    :param project: Optional. Comma seperated lowercase list of MetaBrainz projects to filter by. If not specified, all projects are included.
    :param count: Optional. Number of notifications to fetch. Defaults to :data:`~DEFAULT_NOTIFICATION_FETCH_COUNT`.
    :param offset: Optional. Offset for pagination. Defaults to 0.
    :param until_ts: Optional. Upper bound for the notification timestamp(as a UNIX epoch). Defaults to the current time.
    :param unread_only: Optional. If set to ``t``, only unread notifications are returned. If set to ``f`` or omitted, both unread and read notifications are returned.
    :statuscode 200: Notifications fetched successfully.
    :statuscode 400: Invalid parameters were provided.
    :resheader Content-Type: *application/json*

    """
    token = g._access_token
    user_id = token.owner_id

    count = request.args.get('count')
    if count is None:
        count = DEFAULT_NOTIFICATION_FETCH_COUNT
    else:
        count = int(count)

    offset = request.args.get('offset')
    if offset is None:
        offset = 0
    else:
        offset = int(offset)

    until_ts = request.args.get('until_ts')
    if until_ts is None:
        until_ts = datetime.now(timezone.utc)
    else:
        try:
            until_ts = datetime.fromtimestamp(float(until_ts), tz=timezone.utc)
        except ValueError:
            return Response('Invalid Until_Timestamp ', 400)

    project = request.args.get('project')
    projects=[]
    if project is None:
        for e in NotificationProjectType:
            projects.append(e.value)
    else:
        projects = project.split(',')
        for p in projects:
            try:
                NotificationProjectType(p)
            except ValueError:
                return Response(f'Invalid Project Type{p}\n', 400)

    unread_only = request.args.get('unread_only')
    if unread_only is None or unread_only == 'f':
        unread_only=False
    elif unread_only == 't':
        unread_only=True

    data = fetch_notifications(user_id, projects, count, offset, until_ts, unread_only)
    return jsonify(data)


@notification_bp.post("/mark-read")
@token_required
def mark_notifications():
    """
    Mark notifications as read or unread for a user.
    An access token (available at https://metabrainz.org/profile) must be provided in the Authorization header.

    The request must include a JSON body with at least one of the ``read`` or ``unread`` arrays containing notification ID's.

    Example request body:

    .. code-block:: json

        {
            "read": [1, 2],
            "unread": [3]
        }

    Example successful response:

    .. code-block:: json

        {
            "status": "ok"
        }
    
    :reqheader Authorization: Token <access token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: Notifications successfully updated.
    :statuscode 400: Invalid input.
    :statuscode 403: One or more IDs do not belong to the user.
    :statuscode 500: Internal error, notifications could not be updated.
    :resheader Content-Type: *application/json*
    """
    token = g._access_token
    user_id = token.owner_id

    data = request.json
    if not data:
        return Response('Invalid Input', 400)
    read = data.get('read', [])
    unread = data.get('unread', [])

    # Validate read/unread data
    if not read and not unread:
        return Response('Missing Read and Unread IDs', 400)
    if read:
        if isinstance(read, list):
            if all(isinstance(i, int) for i in read):
                pass
            else:
                return Response('Read values must be Integers', 400)
        else:
            return Response("'read' must be an Array", 400)
    if unread:
        if isinstance(unread, list):
            if all(isinstance(i, int) for i in unread):
                pass
            else:
                return Response('Unread values must be Integers', 400)
        else:
            return Response("'unread' must be an Array", 400)

    notification_ids = read+unread
    if len(notification_ids) == 0:
        return Response("Missing 'read' and 'unread' Array", 400)

    if not validate_notification_ids_for_user(user_id, tuple(notification_ids)):
        return Response("Invalid ID/IDs provided", 403)

    rows_affected = mark_read_unread(user_id, tuple(read), tuple(unread))

    if rows_affected == len(notification_ids):
        return jsonify({'status': 'ok'}), 200
    else:
        return jsonify({'status': 'error', 'message':'Notifications werent updated'}), 500

    
@notification_bp.post("/delete")
@token_required
def remove_notifications():
    """
    Delete notifications for a user.
    An access token (available at https://metabrainz.org/profile) must be provided in the Authorization header.

    The request must include a JSON array of notification IDs that belongs to the user.

    Example request body:

    .. code-block:: json

        [12, 13, 14]

    Example successful response:

    .. code-block:: json

        {
            "status": "ok"
        }

    :reqheader Authorization: Token <access token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: Notifications successfully deleted.
    :statuscode 400: Invalid input.
    :statuscode 403: One or more IDs do not belong to the user.
    :statuscode 500: Internal error, notifications could not be deleted.
    :resheader Content-Type: *application/json*

    """
    token = g._access_token
    user_id = token.owner_id

    delete_ids = request.json
    if not delete_ids:
        return Response('Missing notification IDs for deletion', 400)
    if isinstance(delete_ids, list):
            if all(isinstance(j, int) for j in delete_ids):
                pass
            else:
                return Response('ID values must be Integers', 400)
    else:
        return Response("ID's must be in an Array", 400)
    
    if not validate_notification_ids_for_user(user_id, tuple(delete_ids)):
        return Response("Invalid ID/IDs provided", 403)

    res = delete_notifications(user_id, tuple(delete_ids))
    if res:
        return jsonify({'status': 'ok'}), 200
    else:
        return jsonify({'status': 'error', 'message':'Notifications werent deleted'}), 500
    