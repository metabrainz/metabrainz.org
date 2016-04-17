BEGIN;

ALTER TABLE donation RENAME TO payment;

ALTER TABLE payment ADD COLUMN is_donation BOOLEAN;
-- All existing are donations.
UPDATE payment SET is_donation = TRUE;
ALTER TABLE payment ALTER COLUMN is_donation SET NOT NULL;

ALTER TABLE payment ADD COLUMN invoice_number INTEGER;

ALTER TABLE payment ALTER COLUMN can_contact DROP NOT NULL;
ALTER TABLE payment ALTER COLUMN anonymous DROP NOT NULL;

COMMIT;
