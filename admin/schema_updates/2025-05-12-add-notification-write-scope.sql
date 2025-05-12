BEGIN;

INSERT INTO oauth.scope (name, description)
    VALUES ('notification:write', 'Write notification to notifications table.');

COMMIT;
