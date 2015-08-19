BEGIN;

ALTER TABLE "user" DROP COLUMN payment_method;

COMMIT;
