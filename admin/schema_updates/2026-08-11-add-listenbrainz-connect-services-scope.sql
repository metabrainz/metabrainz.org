BEGIN;

INSERT INTO oauth.scope (name, description, restricted)
    VALUES ('listenbrainz:connect-services', 'Connect external services to your ListenBrainz account.', TRUE);

COMMIT;
