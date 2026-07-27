BEGIN;

UPDATE oauth.scope
   SET name = 'musicbrainz:tag'
 WHERE name = 'tag';

UPDATE oauth.scope
   SET name = 'musicbrainz:rating'
 WHERE name = 'rating';

INSERT INTO oauth.scope (name, description)
    VALUES ('email', 'View your email address'),
           ('musicbrainz:collection', 'View and modify your private collections'),
           ('musicbrainz:submit_isrc', 'Submit new ISRCs to the database'),
           ('musicbrainz:submit_barcode', 'Submit new barcodes to the database');

COMMIT;
