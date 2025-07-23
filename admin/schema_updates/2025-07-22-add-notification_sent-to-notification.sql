BEGIN;

ALTER TABLE notification ADD COLUMN notification_sent BOOL DEFAULT FALSE;

END;