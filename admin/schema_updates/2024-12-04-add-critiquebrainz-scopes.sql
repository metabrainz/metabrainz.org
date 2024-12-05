BEGIN;

INSERT INTO oauth.scope (name, description)
    VALUES ('critiquebrainz:review', 'Create and modify CritiqueBrainz reviews.'),
           ('critiquebrainz:vote', 'Submit and delete votes on CritiqueBrainz reviews.'),
           ('critiquebrainz:profile', 'Modify profile info and delete profile on CritiqueBrainz.');

COMMIT;
