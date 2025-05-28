import sqlalchemy
from datetime import datetime
from typing import List, Tuple
from flask import current_app

from metabrainz import db

def fetch_notifications(user_id: int, projects: List[str], count: int, offset: int, until_ts: datetime, unread_only: bool ) -> List[dict]:
    """Fetches notifications for a given user based on provided args.

    Args:
        user_id (int): User's row id from User table. (musicbrainz_row_id for now)
        projects (List[str]): List of MetaBrainz projects from which notifications are to be fetched.
        count (int): Number of notifications to fetch.
        offset (int): Number of notifications to skip (for pagination).
        until_ts (datetime): Upper limit timestamp for notifications.
        unread_only (bool): Whether to fetch only unread notifications.

    Returns:
        List[dict]: List of dictionaries containing the fetched notifications in descending order of their created timestamp.
    """

    params = {
        "user_id": user_id,
        "projects": tuple(projects),
        "count": count,
        "offset": offset,
        "until_ts": until_ts,
        "unread_only": unread_only
    }

    with db.engine.connect() as connection:
        query = sqlalchemy.text("""
                SELECT
                        id,
                        musicbrainz_row_id,
                        project::TEXT,
                        body,
                        template_id,
                        created,
                        read,
                        important
                FROM
                        notification    
                WHERE
                        musicbrainz_row_id = :user_id
                        AND created <= :until_ts
                        AND project in :projects
                        AND (:unread_only = FALSE OR read = FALSE)
                ORDER BY
                        created DESC
                LIMIT
                        :count
                OFFSET
                        :offset
        """)
        
        result = connection.execute(query, params).fetchall()
        return [
            {"id": r.id, "user_id": r.musicbrainz_row_id, "project": r.project, "body": r.body,
            "template_id": r.template_id,"sent_at": r.created, "read": r.read, "important": r.important} for r in result
            ]


def validate_notification_ids_for_user(user_id: int, notification_ids: Tuple[int, ...]) -> bool:
    """Verifies if the notification IDs belong to the user.

    Args:
        user_id (int): User's row id from User table. (musicbrainz_row_id for now)
        notification_ids (Tuple[int, ...]): Tuple of Notification row Ids from Notification table.
    
    Returns:
        bool: Whether all the notifications belong to the user.
    """

    with db.engine.connect() as connection:
        query = sqlalchemy.text("""
                SELECT 
                        COUNT(id)
                FROM
                        notification
                WHERE
                        musicbrainz_row_id = :user_id
                        AND id IN :notification_ids
        """)

        result = connection.execute(query, {'user_id': user_id, 'notification_ids': notification_ids}).scalar()
        return result == len(notification_ids)


def mark_read_unread(user_id: int, read_ids: Tuple[int, ...], unread_ids: Tuple[int, ...]) -> int:
    """Marks specified notifications as read or unread for a given user.

    Args:
        user_id (int): User's row id from User table. (musicbrainz_row_id for now)
        read_ids (Tuple[int, ...]): Tuple of notification IDs to be marked as read.
        unread_ids (Tuple[int, ...]): Tuple of notification IDs to be be marked as unread.
    
    Returns:
        int : Total number of rows successfully updated. -1 if a database error occurs.
    """

    total_affected_rows=0
    try:
        with db.engine.connect() as connection:
            read_query = sqlalchemy.text("""
                            UPDATE
                                    notification
                            SET 
                                    read = TRUE
                            WHERE
                                    musicbrainz_row_id = :user_id
                                    AND id IN :read_ids
            """)
            if read_ids:
                result_read = connection.execute(read_query, {'user_id': user_id, 'read_ids': read_ids})
                total_affected_rows += result_read.rowcount

            unread_query = sqlalchemy.text("""
                            UPDATE
                                    notification
                            SET 
                                    read = FALSE
                            WHERE
                                    musicbrainz_row_id = :user_id
                                    AND id IN :unread_ids
            """)
            if unread_ids:
                result_unread = connection.execute(unread_query, {'user_id': user_id, 'unread_ids': unread_ids})
                total_affected_rows+= result_unread.rowcount

    except  Exception as e:
            current_app.logger.exception(e)
            total_affected_rows=-1

    return  total_affected_rows


def delete_notifications(user_id: int, delete_ids: Tuple[int, ...]) -> bool:
    """Deletes specified notifications for a given user.
    Args:
        user_id (int): User's row id from User table. (musicbrainz_row_id for now)
        delete_ids (Tuple[int, ...]): Tuple of notification IDs to be deleted.
    
    Returns:
        bool: True if the deletion operation occurs without any error else False.
    """

    try:
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
            return True
    
    except Exception as e:
        current_app.logger.exception(e)
        return False
