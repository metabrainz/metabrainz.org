from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timezone
from metabrainz.model.notification import NotificationProjectType
from metabrainz.db.notification import fetch_notifications, mark_read_unread, delete_notifications
from metabrainz.errors import APIBadRequest, APIServiceUnavailable

DEFAULT_NOTIFICATION_FETCH_COUNT = 100
MAX_ITEMS_PER_GET = 1000 # From listenbrainz.webserver.views.api_tools


notification_bp = Blueprint("notification", __name__)


@notification_bp.get("/<int:user_id>/fetch")
# TODO: Add authorization decorator.
def get_notifications(user_id: int):
    """
    Fetch notifications for a user.
    An access token must be provided as a query paramater.
    
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

    :param token: Required. Access token for authentication.
    :param project: Optional. Comma seperated lowercase list of MetaBrainz projects to filter by. If not specified, all projects are included.
    :param count: Optional. Number of notifications to fetch. Must be in the range of [1, :data:`~MAX_ITEMS_PER_GET`]. Defaults to :data:`~DEFAULT_NOTIFICATION_FETCH_COUNT`.
    :param offset: Optional. Offset for pagination. Must be a non negative integer. Defaults to 0. 
    :param until_ts: Optional. Upper bound for the notification timestamp(as a UNIX epoch). Defaults to the current time.
    :param unread_only: Optional. If set to ``t``, only unread notifications are returned. If set to ``f`` or omitted, both unread and read notifications are returned.
    :statuscode 200: Notifications fetched successfully.
    :statuscode 400: Invalid parameters were provided.
    :resheader Content-Type: *application/json*

    """
    
    count = request.args.get('count')
    if count is None:
        count = DEFAULT_NOTIFICATION_FETCH_COUNT
    else:
        count = int(count)
        if not (count >= 1 and count <= MAX_ITEMS_PER_GET):
            raise APIBadRequest('Invalid count')

    offset = request.args.get('offset')
    if offset is None:
        offset = 0
    else:
        offset = int(offset)
        if offset < 0:
            raise APIBadRequest('Invalid offset')

    until_ts = request.args.get('until_ts')
    if until_ts is None:
        until_ts = datetime.now(timezone.utc)
    else:
        try:
            until_ts = datetime.fromtimestamp(float(until_ts), tz=timezone.utc)
        except ValueError:
            raise APIBadRequest('Invalid Until_Timestamp ')

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
                raise APIBadRequest(f'Invalid Project Type{p}\n')

    unread_only = request.args.get('unread_only')
    if unread_only is None or unread_only == 'f':
        unread_only=False
    elif unread_only == 't':
        unread_only=True

    # data = fetch_notifications(user_id, tuple(projects), count, offset, until_ts, unread_only)
    data = fetch_notifications(user_id=user_id)
    return jsonify(data)


@notification_bp.post("<int:user_id>/mark-read")
# TODO: Add authorization decorator.
def mark_notifications(user_id: int):
    """
    Mark notifications as read or unread for a user.
    An access token must be provided as a query paramater.

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
    
    :param token: Required. Access token for authentication.
    :reqheader Content-Type: *application/json*
    :statuscode 200: Notifications successfully updated.
    :statuscode 400: Invalid input.
    :resheader Content-Type: *application/json*

    """

    data = request.json
    if not data:
        raise APIBadRequest('Invalid Input')
    read = data.get('read', [])
    unread = data.get('unread', [])

    # Validate read/unread data
    if not read and not unread:
        raise APIBadRequest('Missing Read and Unread IDs')
    if read:
        if isinstance(read, list):
            if all(isinstance(i, int) for i in read):
                pass
            else:
                raise APIBadRequest('Read values must be Integers')
        else:
            raise APIBadRequest("'read' must be an Array")
    if unread:
        if isinstance(unread, list):
            if all(isinstance(i, int) for i in unread):
                pass
            else:
                raise APIBadRequest('Unread values must be Integers')
        else:
            raise APIBadRequest("'unread' must be an Array")
    try:
        mark_read_unread(user_id, tuple(read), tuple(unread))
    except Exception as err:
        current_app.logger.error("Cannot update read values ", str(err))
        raise APIServiceUnavailable("Cannot update read values right now.")

    return jsonify({'status': 'ok'}), 200


@notification_bp.post("<int:user_id>/delete")
# TODO: Add Authorization decorator.
def remove_notifications(user_id: int):
    """
    Delete notifications for a user.
    An access token must be provided as a query paramater.

    The request must include a JSON array of notification IDs that belongs to the user.

    Example request body:

    .. code-block:: json

        [12, 13, 14]

    Example successful response:

    .. code-block:: json

        {
            "status": "ok"
        }

    :param token: Required. Access token for authentication.
    :reqheader Content-Type: *application/json*
    :statuscode 200: Notifications successfully deleted.
    :statuscode 400: Invalid input.
    :resheader Content-Type: *application/json*

    """

    delete_ids = request.json
    if not delete_ids:
        raise APIBadRequest('Missing notification IDs for deletion')
    
    # Validate delete_ids array.
    if isinstance(delete_ids, list):
            if all(isinstance(j, int) for j in delete_ids):
                pass
            else:
                raise APIBadRequest('ID values must be Integers')
    else:
        raise APIBadRequest("ID's must be in an Array")
    try:
        delete_notifications(user_id, tuple(delete_ids))
    except Exception as err:
        current_app.logger.error("Cannot delete notifications ", str(err))
        raise APIServiceUnavailable("Cannot delete notifications right now.")

    return jsonify({'status': 'ok'}), 200
    