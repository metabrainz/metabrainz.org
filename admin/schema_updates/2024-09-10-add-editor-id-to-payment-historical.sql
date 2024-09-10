-- after running python manage.py import-musicbrainz-row-ids command

BEGIN;

UPDATE payment p
   SET editor_id = s.musicbrainz_row_id
  FROM supporter s
 WHERE p.editor_name = s.musicbrainz_id;

COMMIT;
