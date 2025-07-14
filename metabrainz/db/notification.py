import sqlalchemy
import uuid
import orjson
from datetime import datetime
from typing import List, Tuple, Optional
from flask import current_app

from metabrainz import db


def fetch_notifications(user_id: int, projects: Optional[Tuple[str, ...]]=None, count: Optional[int]=None, offset: Optional[int]=None,
                        until_ts: Optional[datetime]=None, unread_only: Optional[bool]=False ) -> List[dict]:

    """Fetches notifications for a given user based on provided args.

    Args:
        user_id (int): User's row id from User table. (musicbrainz_row_id for now)
        projects (Optional[Tuple[str, ...]]): List of MetaBrainz projects from which notifications are to be fetched.
        count (Optional[int]): Number of notifications to fetch.
        offset (Optional[int]): Number of notifications to skip (for pagination).
        until_ts (Optional[datetime]): Upper limit timestamp for notifications.
        unread_only (Optional[bool]): Whether to fetch only unread notifications.

    Returns:
        List[dict]: List of dictionaries containing the fetched notifications in descending order of their created timestamp.
    """

    if not projects:
        projects = (None, )
    params = {
        "user_id": user_id,
        "projects": projects,
        "count": count,
        "offset": offset,
        "until_ts": until_ts,
        "unread_only": unread_only
    }

    with db.engine.connect() as connection:
        query = sqlalchemy.text("""
                SELECT
                        id
                        ,musicbrainz_row_id AS user_id
                        ,project::TEXT
                        ,body
                        ,template_id
                        ,created AS sent_at
                        ,read
                        ,important
                FROM
                        notification    
                WHERE
                        musicbrainz_row_id = :user_id
                        AND (:until_ts IS NULL OR created <= :until_ts)
                        AND (:projects IS NULL OR project IN :projects)
                        AND (:unread_only = FALSE OR read = FALSE)
                ORDER BY
                        created DESC
                LIMIT
                        :count
                OFFSET
                        :offset
        """)
        
        result = connection.execute(query, params)
        return [dict(row) for row in result.mappings()]


def mark_read_unread(user_id: int, read_ids: Tuple[int, ...], unread_ids: Tuple[int, ...]) -> int:
    """Marks specified notifications as read or unread for a given user.

    Args:
        user_id (int): User's row id from User table. (musicbrainz_row_id for now)
        read_ids (Tuple[int, ...]): Tuple of notification IDs to be marked as read.
        unread_ids (Tuple[int, ...]): Tuple of notification IDs to be be marked as unread.
    
    Returns:
        int : Total number of rows successfully updated.

    """

    if not read_ids:
        read_ids = (None, )
    if not unread_ids:
        unread_ids = (None, )

    with db.engine.connect() as connection:
        read_query = sqlalchemy.text("""
                        UPDATE
                                notification
                        SET 
                                read =  CASE
                                            WHEN id in :read_ids THEN TRUE
                                            ELSE FALSE
                                        END
                        WHERE
                                musicbrainz_row_id = :user_id
                                AND (id IN :read_ids OR id IN :unread_ids)
        """)
        total_affected_rows = connection.execute(read_query, {'user_id': user_id, 'read_ids': read_ids, 'unread_ids': unread_ids}).rowcount
        
    return  total_affected_rows


def delete_notifications(user_id: int, delete_ids: Tuple[int, ...]):
    """Deletes specified notifications for a given user.
    Args:
        user_id (int): User's row id from User table. (musicbrainz_row_id for now)
        delete_ids (Tuple[int, ...]): Tuple of notification IDs to be deleted.
    
    """
    if not delete_ids:
        delete_ids = (None, )

    with db.engine.connect() as connection:
        delete_query = sqlalchemy.text("""
                        DELETE
                        FROM
                                notification
                        WHERE
                                musicbrainz_row_id = :user_id
                                AND id IN :delete_ids
        """)
        connection.execute(delete_query, {'user_id': user_id, 'delete_ids': delete_ids})


def insert_notifications(notifications: List[dict]) -> int:
    """
    Inserts a batch of notifications into the table.
    Args:
        notifications (List[dict]): List of notifications to be inserted.

    Returns:
        int : Total number of rows successfully inserted.
    """
    params = _prepare_notifications(notifications)
    with db.engine.connect() as connection:
        insert_query = sqlalchemy.text("""
                    INSERT INTO
                        notification
                            (musicbrainz_row_id, project, subject, body, template_id, template_params, important, expire_age, email_id, read)
                    VALUES
                        (:musicbrainz_row_id, :project, :subject, :body, :template_id, :template_params, :important, :expire_age, :email_id, :read)        
        """)
        result = connection.execute(insert_query, params)
    return result.rowcount


def _prepare_notifications(notifications: List[dict]) -> List[dict]:
    """Helper function to prepare notifications for insertion into db."""

    params = []
    for notif in notifications:
        params.append(
            {
                "musicbrainz_row_id": notif["user_id"],
                "project": notif["project"],
                "important": notif["important"],
                "expire_age": notif["expire_age"],
                "email_id": notif.get("email_id", str(uuid.uuid4())),
                "read": False,
                "subject": notif.get("subject"),
                "body": notif.get("body"),
                "template_id": notif.get("template_id"),
                "template_params": (
                    orjson.dumps(notif.get("template_params")).decode("utf-8")
                    if notif.get("template_params")
                    else None
                ),
            }
        )

    return params


def filter_non_digest_notifications(notifications: List[dict]) -> List[dict]:
    """Filter notifications which belongs to users with digest disabled.
    Args:
        notifications (List[dict]): List of notifications.
    Returns:
        List[dict] : List of notifications for users with digest disabled.

    """
    user_ids_to_check = tuple(i["user_id"] for i in notifications)
    with db.engine.connect() as connection:
        query = sqlalchemy.text("""
                        SELECT musicbrainz_row_id
                        FROM user_preference
                        WHERE musicbrainz_row_id IN :user_ids AND digest = FALSE
        """)
        result = connection.execute(query, {"user_ids": user_ids_to_check})
        non_digest_user_ids = {user_id[0] for user_id in result}

    non_digest_notifications = []
    for notification in notifications:
        if notification["user_id"] in non_digest_user_ids:
            non_digest_notifications.append(notification)

    return non_digest_notifications


def delete_expired_notifications():
    with db.engine.connect() as connection:
        query = sqlalchemy.text(
            """
                DELETE
                FROM  
                    notification
                WHERE 
                    (created + (INTERVAL '1 day' * expire_age)) <= NOW()
            """
        )
        result = connection.execute(query)
    current_app.logger.info(f"Deleted {result.rowcount} notifications.")


def get_digest_notifications() -> List[dict]:
    with db.engine.connect() as connection:
        query = sqlalchemy.text(
            """
                SELECT 
                        notification.musicbrainz_row_id
                        ,notification.subject
                        ,notification.body
                        ,notification.template_id
                        ,notification.template_params
                        ,user_preference.user_email
                        ,notification.project::TEXT
                FROM
                        notification
                JOIN
                        user_preference ON notification.musicbrainz_row_id = user_preference.musicbrainz_row_id

                WHERE
                        user_preference.digest = true
                        AND (notification.created + (INTERVAL '1 day' * user_preference.digest_age)) <= NOW()
                        AND notification.read = false      
            """
        )
        result = connection.execute(query)

        notifications = []
        for row in result.mappings():
            row = dict(row)
            row["to"] = row["user_email"]
            row["from_addr"] = f'no_reply@{row["project"]}.org'
            notifications.append(row)

        return notifications
