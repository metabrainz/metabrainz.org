BEGIN;

DROP TABLE IF EXISTS "user"             CASCADE;
DROP TABLE IF EXISTS payment            CASCADE;
DROP TABLE IF EXISTS oauth_grant        CASCADE;
DROP TABLE IF EXISTS oauth_token        CASCADE;
DROP TABLE IF EXISTS oauth_client       CASCADE;
DROP TABLE IF EXISTS access_log         CASCADE;
DROP TABLE IF EXISTS moderation_log     CASCADE;
DROP TABLE IF EXISTS token_log          CASCADE;
DROP TABLE IF EXISTS token              CASCADE;
DROP TABLE IF EXISTS supporter          CASCADE;
DROP TABLE IF EXISTS tier               CASCADE;
DROP TABLE IF EXISTS dataset_supporter  CASCADE;
DROP TABLE IF EXISTS dataset            CASCADE;

COMMIT;
