BEGIN;

ALTER TABLE "user" RENAME TO supporter;
ALTER TABLE dataset_user RENAME TO dataset_supporter;

ALTER TABLE dataset_supporter RENAME COLUMN user_id TO supporter_id;
ALTER TABLE token_log RENAME COLUMN user_id TO supporter_id;

ALTER TABLE supporter RENAME CONSTRAINT user_tier_id_fkey TO supporter_tier_id_fkey;
ALTER TABLE dataset_supporter RENAME CONSTRAINT dataset_user_user_id_fkey TO dataset_supporter_supporter_id_fkey;
ALTER TABLE dataset_supporter RENAME CONSTRAINT dataset_user_dataset_id_fkey TO dataset_supporter_dataset_id_fkey;
ALTER TABLE token_log RENAME CONSTRAINT token_log_user_id_fkey TO token_log_supporter_id_fkey;

ALTER TABLE supporter RENAME CONSTRAINT user_pkey TO supporter_pkey;
ALTER TABLE dataset_supporter RENAME CONSTRAINT dataset_user_pkey TO dataset_supporter_pkey;

COMMIT;