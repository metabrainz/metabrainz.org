BEGIN;

INSERT INTO oauth.scope (name, description)
    VALUES ('notification', 'Fetch or Alter the notifications in MeB notification table.');

COMMIT;

