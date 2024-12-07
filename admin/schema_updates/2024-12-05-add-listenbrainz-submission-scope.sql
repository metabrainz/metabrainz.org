BEGIN;

INSERT INTO oauth.scope (name, description)
    VALUES ('listenbrainz:submit-listens', 'Submit listens to ListenBrainz.');

COMMIT;
