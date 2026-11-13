BEGIN;

INSERT INTO oauth.scope (name, description, restricted)
    VALUES ('synapse:notifications:inbox', 'View your notifications and mark them as read.', TRUE)
         , ('synapse:notifications', 'View and manage your notifications and how you receive them.', TRUE);

COMMIT;
