BEGIN;

ALTER TABLE "user" RENAME COLUMN short_descr TO data_usage_desc;
ALTER TABLE "user" RENAME COLUMN long_descr TO org_desc;

COMMIT;
