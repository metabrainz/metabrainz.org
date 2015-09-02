BEGIN;

ALTER TABLE access_log ADD COLUMN ip_address INET;

COMMIT;
