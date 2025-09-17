import sqlalchemy
import uuid
import orjson
from datetime import datetime
from typing import List, Tuple, Optional
from flask import current_app
from brainzutils.mail import send_mail

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

    params=[]
    for notif in notifications:
        params.append({
            "musicbrainz_row_id": notif["musicbrainz_row_id"]
            ,"project": notif["project"]
            ,"subject":notif.get("subject")
            ,"body" : notif.get("body")
            ,"template_id": notif.get("template_id")
            ,"template_params": orjson.dumps(notif.get("template_params")).decode("utf-8") if notif.get("template_params") else None
            ,"important": notif["important"]
            ,"expire_age": notif["expire_age"]
            ,"email_id": notif.get("email_id", str(uuid.uuid4()))
            ,"read": False
        })

        if notif["important"] and notif["send_email"] and notif["project"] in current_app.config['MAIL_FROM_PROJECTS']:
            addr = current_app.config['MAIL_FROM_PROJECTS'][notif["project"]]
            try:
                send_mail(
                    subject=notif["subject"],
                    text=notif["body"],
                    recipients=list(notif["to"]),
                    from_addr='noreply@' + addr
                )
            except Exception:
                current_app.logger.error("Could not send email to %s", notif["to"]) 
            params[-1]["read"] = True

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

