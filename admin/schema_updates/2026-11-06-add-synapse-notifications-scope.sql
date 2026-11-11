BEGIN;

INSERT INTO oauth.scope (name, description, restricted)
    VALUES ('synapse:notifications', 'View and manage your notifications and how you receive them.', TRUE);

COMMIT;
