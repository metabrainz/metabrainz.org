import sqlalchemy
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
        int : Total number of rows successfully updated. -1 if a database error occurs.
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

