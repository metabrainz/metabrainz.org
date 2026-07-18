"""Migrate users from the MusicBrainz ``editor`` table into the MetaBrainz ``user`` table.

The two tables live in different databases, so this is done over the network with a
plain Python script: MusicBrainz editors are streamed from the MusicBrainz database
(``SQLALCHEMY_MUSICBRAINZ_URI``) and inserted into the MetaBrainz database
(``SQLALCHEMY_DATABASE_URI``).

The script is idempotent, resumable and incremental. It can be re-run after an
interruption or repeatedly to keep the tables in sync: editors are upserted, and an
existing user is only updated when the MusicBrainz ``editor.last_updated`` is newer than
the stored ``user.last_updated`` or when an earlier run stored a source-format password
that must be normalized. Updates only touch MusicBrainz-owned columns and preserve
MetaBrainz-owned state (``login_id`` and ``is_blocked``).

Editors and users are matched by row id throughout: ``user.id`` holds the MusicBrainz
``editor.id``, so a MusicBrainz name change is just another column to copy across and never
affects which rows are matched.

Re-runs only read the editors that changed since the previous run. Each completed run
records in ``mb_import_state`` the MusicBrainz time at which it *started* reading, and the
next run resumes from that watermark minus an overlap window. Both adjustments exist to
avoid missing rows, and cover the two ways a change can escape a run:

* An editor changed while the copy was running, at an id the scan had already passed. Its
  ``last_updated`` is at or after the run's start time, so starting the next run there
  re-reads it. This is why the watermark is the start time rather than the newest
  ``last_updated`` actually seen, which would sit past such a change and skip it.
* An editor stamped before the run started but only committed after the scan read that id.
  Its ``last_updated`` can be arbitrarily far behind the watermark, so the overlap window
  is what brings it back into range.

Re-reading is cheap in both cases: unchanged editors are filtered out before any write. The
first run has no watermark and therefore reads the whole ``editor`` table. Pass
``full=True`` to force a complete re-read, which is also how editors with a NULL
``editor.last_updated`` are picked up, since an incremental run cannot place them relative
to the watermark.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg2
from flask import current_app
from psycopg2.extras import RealDictCursor, execute_values

from metabrainz import bcrypt, db

# Number of editors to read from MusicBrainz and write to MetaBrainz per batch.
DEFAULT_BATCH_SIZE = 1000
DEFAULT_MEMBER_SINCE = datetime(1970, 1, 1, tzinfo=timezone.utc)
# How far back before the watermark an incremental run starts reading. An editor row can
# become visible to us with a last_updated older than a watermark we already stored (a
# long-running MusicBrainz transaction that set last_updated before it committed, or clock
# skew between the two servers), so re-reading a window of overlap keeps those rows from
# being missed forever. Re-read rows are cheap: unchanged ones are filtered out before any
# write.
DEFAULT_OVERLAP = timedelta(hours=1)
# test.mb stores passwords as "{CLEARTEXT}..." and can have many users. Use a low
# migration-only bcrypt cost so local/test imports do not spend minutes hashing.
DEFAULT_CLEARTEXT_PASSWORD_LOG_ROUNDS = 4
CRYPT_PASSWORD_PREFIX = "{CRYPT}"
CLEARTEXT_PASSWORD_PREFIX = "{CLEARTEXT}"

# The next run's watermark, read before any editor is. now() is the transaction start time,
# so every change committed while this run is copying is stamped at or after it and gets
# re-read next time. Taking the newest last_updated actually seen instead would skip any
# editor changed during the run at an id the scan had already passed.
#
# It must come from the MusicBrainz clock, not ours: it is compared against
# editor.last_updated values, which that server stamped.
FETCH_SOURCE_TIME_QUERY = "SELECT now()"

FETCH_EDITORS_QUERY = """
    SELECT id,
           name,
           email,
           email_confirm_date,
           member_since,
           last_login_date,
           last_updated,
           password,
           deleted
      FROM editor
     WHERE id > %(after_id)s
       AND (%(since)s::timestamptz IS NULL OR last_updated >= %(since)s)
  ORDER BY id
     LIMIT %(batch_size)s
"""

# Identifies this importer's row in mb_import_state; not a MusicBrainz editor name. The
# watermark is kept in that table rather than derived from MAX(user.last_updated), because
# MetaBrainz writes user.last_updated itself (email confirmation, admin edits) and that
# would push the watermark past editors that were never imported.
IMPORTER_NAME = "user"

FETCH_WATERMARK_QUERY = "SELECT last_updated FROM mb_import_state WHERE importer = %(importer)s"

# Only ever move the watermark forward, so a --full or narrowed re-run cannot rewind it.
STORE_WATERMARK_QUERY = """
    INSERT INTO mb_import_state (importer, last_updated)
         VALUES (%(importer)s, %(last_updated)s)
    ON CONFLICT (importer) DO UPDATE
       SET last_updated = EXCLUDED.last_updated
     WHERE EXCLUDED.last_updated > mb_import_state.last_updated
"""

# Fetch users already imported, so we can decide which editors in a batch are new,
# changed, unchanged or need password normalization.
FETCH_EXISTING_QUERY = 'SELECT id, last_updated, password FROM "user" WHERE id = ANY(%(ids)s)'

# Upsert a single editor. login_id and is_blocked are deliberately left out of the
# DO UPDATE clause: login_id is generated by MetaBrainz on first import (re-generating it
# would invalidate active sessions) and is_blocked is MetaBrainz-owned moderation state.
# The DO UPDATE WHERE clause is a race guard: even if a row is sent, an older MusicBrainz
# change can never overwrite a newer one except to normalize a source-format password
# previously written by this importer.
UPSERT_USER_QUERY = """
    INSERT INTO "user" (id, login_id, name, password, email, unconfirmed_email,
                        email_confirmed_at, member_since, last_login_at, last_updated, deleted)
         VALUES %s
    ON CONFLICT (id) DO UPDATE
       SET name = EXCLUDED.name,
           password = EXCLUDED.password,
           email = EXCLUDED.email,
           unconfirmed_email = EXCLUDED.unconfirmed_email,
           email_confirmed_at = EXCLUDED.email_confirmed_at,
           member_since = EXCLUDED.member_since,
           last_login_at = EXCLUDED.last_login_at,
           last_updated = EXCLUDED.last_updated,
           deleted = EXCLUDED.deleted
     WHERE EXCLUDED.last_updated > "user".last_updated
        OR (
           ("user".password LIKE '{CRYPT}%%' OR "user".password LIKE '{CLEARTEXT}%%')
           AND (EXCLUDED.last_updated >= "user".last_updated OR "user".last_updated IS NULL)
        )
"""

UPSERT_USER_TEMPLATE = (
    "(%(id)s, %(login_id)s, %(name)s, %(password)s, %(email)s, %(unconfirmed_email)s, "
    "%(email_confirmed_at)s, %(member_since)s, %(last_login_at)s, %(last_updated)s, %(deleted)s)"
)


def _password_needs_normalization(password):
    password = password or ""
    return (
        password.startswith(CRYPT_PASSWORD_PREFIX)
        or password.startswith(CLEARTEXT_PASSWORD_PREFIX)
    )


def _normalize_musicbrainz_password(password, cleartext_password_log_rounds=DEFAULT_CLEARTEXT_PASSWORD_LOG_ROUNDS):
    password = password or ""
    if password.startswith(CRYPT_PASSWORD_PREFIX):
        return password[len(CRYPT_PASSWORD_PREFIX):]
    if password.startswith(CLEARTEXT_PASSWORD_PREFIX):
        password = password[len(CLEARTEXT_PASSWORD_PREFIX):]
        return bcrypt.generate_password_hash(password, rounds=cleartext_password_log_rounds).decode("utf-8")
    return password


def _build_user_row(editor, cleartext_password_log_rounds=DEFAULT_CLEARTEXT_PASSWORD_LOG_ROUNDS):
    """Map a MusicBrainz editor row to the parameters for an upsert into ``user``.

    ``login_id`` is only consumed on the INSERT path; the upsert never updates it, so an
    existing user keeps its original login_id (and therefore its active sessions).
    """
    deleted = editor["deleted"]

    if deleted:
        # Deleted editors are already anonymised in MusicBrainz; do not carry over any
        # password or email and keep the password column non-null as the schema requires.
        password = ""
        email = None
        unconfirmed_email = None
        email_confirmed_at = None
    else:
        # MusicBrainz production stores bcrypt in RFC 2307 "{CRYPT}" form; test.mb can
        # store "{CLEARTEXT}" passwords. MetaBrainz stores only bcrypt-compatible hashes.
        password = _normalize_musicbrainz_password(editor["password"], cleartext_password_log_rounds)

        if editor["email"] and editor["email_confirm_date"]:
            email = editor["email"]
            unconfirmed_email = None
            email_confirmed_at = editor["email_confirm_date"]
        else:
            email = None
            unconfirmed_email = editor["email"]
            email_confirmed_at = None

    return {
        "id": editor["id"],
        "login_id": str(uuid4()),
        "name": editor["name"],
        "password": password,
        "email": email,
        "unconfirmed_email": unconfirmed_email,
        "email_confirmed_at": email_confirmed_at,
        "member_since": editor["member_since"] or DEFAULT_MEMBER_SINCE,
        "last_login_at": editor["last_login_date"],
        "last_updated": editor["last_updated"],
        "deleted": deleted,
    }


def _upsert_batch(meb_cursor, rows):
    """Upsert a batch of user rows in a single statement and return the number written.

    page_size is forced to the row count so execute_values emits one statement, which
    makes rowcount accurate (number of rows actually inserted or updated).
    """
    if not rows:
        return 0
    execute_values(meb_cursor, UPSERT_USER_QUERY, rows,
                   template=UPSERT_USER_TEMPLATE, page_size=len(rows))
    return meb_cursor.rowcount


def _needs_write(editor, existing_user):
    """Decide whether an editor must be (re-)written, to avoid unnecessary writes.

    New editors always need a write. An existing user is rewritten when MusicBrainz
    has a strictly newer ``last_updated`` than what we previously imported, or when an
    earlier run stored a source-format password that now needs normalization.
    """
    if existing_user is None:
        return True

    editor_last_updated = editor["last_updated"]
    existing_last_updated = existing_user["last_updated"]

    if existing_last_updated is None:
        return True

    if _password_needs_normalization(existing_user["password"]):
        if editor_last_updated is None:
            return False
        return editor_last_updated >= existing_last_updated

    if editor_last_updated is None:
        return False
    return editor_last_updated > existing_last_updated


def _reset_user_id_sequence(meb_cursor):
    """Advance the ``user.id`` identity sequence past the imported ids.

    The ids are inserted explicitly, which does not advance the identity sequence, so new
    sign-ups would otherwise collide with imported ids.
    """
    meb_cursor.execute("""
        SELECT setval(
            pg_get_serial_sequence('"user"', 'id'),
            GREATEST((SELECT COALESCE(MAX(id), 1) FROM "user"), 1)
        )
    """)


def _fetch_since(meb_cursor, full, overlap):
    """Return the ``editor.last_updated`` an incremental run should start reading from.

    ``None`` means "read every editor": either a full run was requested or nothing has been
    imported yet.
    """
    if full:
        return None

    meb_cursor.execute(FETCH_WATERMARK_QUERY, {"importer": IMPORTER_NAME})
    row = meb_cursor.fetchone()
    if row is None:
        return None
    return row[0] - overlap


def _store_watermark(meb_cursor, watermark):
    """Record where this run started reading, for the next run to start from."""
    meb_cursor.execute(STORE_WATERMARK_QUERY,
                       {"importer": IMPORTER_NAME, "last_updated": watermark})


def migrate_mb_users(batch_size=DEFAULT_BATCH_SIZE,
                     cleartext_password_log_rounds=DEFAULT_CLEARTEXT_PASSWORD_LOG_ROUNDS,
                     full=False,
                     overlap=DEFAULT_OVERLAP):
    """Stream MusicBrainz editors and import them into the MetaBrainz user table."""
    mb_uri = current_app.config["SQLALCHEMY_MUSICBRAINZ_URI"]
    if not mb_uri:
        raise RuntimeError("SQLALCHEMY_MUSICBRAINZ_URI is not configured.")

    meb_connection = db.engine.raw_connection()
    mb_connection = psycopg2.connect(mb_uri)
    try:
        after_id = 0
        total_written = 0
        total_skipped = 0

        with meb_connection.cursor() as meb_cursor, \
                mb_connection.cursor(cursor_factory=RealDictCursor) as mb_cursor:
            # Read before the first batch: this becomes the next run's starting point, so it
            # has to predate everything this run reads.
            mb_cursor.execute(FETCH_SOURCE_TIME_QUERY)
            watermark = mb_cursor.fetchone()["now"]

            since = _fetch_since(meb_cursor, full, overlap)
            if since is None:
                current_app.logger.info("Migrating all MusicBrainz editors.")
            else:
                current_app.logger.info("Migrating MusicBrainz editors changed since %s.", since)

            while True:
                mb_cursor.execute(FETCH_EDITORS_QUERY,
                                  {"after_id": after_id, "batch_size": batch_size, "since": since})
                editors = mb_cursor.fetchall()
                if not editors:
                    break

                # Look up the users we already imported in this batch so we can skip
                # unchanged editors instead of rewriting rows that have not changed.
                meb_cursor.execute(FETCH_EXISTING_QUERY, {"ids": [e["id"] for e in editors]})
                existing = {
                    r[0]: {
                        "last_updated": r[1],
                        "password": r[2],
                    } for r in meb_cursor.fetchall()
                }

                rows = [_build_user_row(editor, cleartext_password_log_rounds) for editor in editors
                        if _needs_write(editor, existing.get(editor["id"]))]
                written = _upsert_batch(meb_cursor, rows)
                # Skipped = unchanged editors filtered out + rows the WHERE guard rejected.
                total_written += written
                total_skipped += len(editors) - written

                # editors are ordered by id, so the last one is the highest id in the batch.
                after_id = editors[-1]["id"]
                meb_connection.commit()
                current_app.logger.info(
                    "Migrated editors up to id %s (written=%s, skipped=%s).",
                    after_id, total_written, total_skipped,
                )

            _reset_user_id_sequence(meb_cursor)
            # Only advance the watermark once the whole range has been read: an interrupted
            # run leaves the old watermark in place and is simply re-read next time.
            _store_watermark(meb_cursor, watermark)
            meb_connection.commit()

        current_app.logger.info(
            "Finished migrating MusicBrainz editors: %s written, %s skipped, watermark %s.",
            total_written, total_skipped, watermark,
        )
        return total_written, total_skipped
    except Exception:
        meb_connection.rollback()
        current_app.logger.error("Error while migrating MusicBrainz editors.", exc_info=True)
        raise
    finally:
        mb_connection.close()
        meb_connection.close()
