BEGIN;

-- Dropping the schema with CASCADE removes all oauth tables along with their primary
-- keys, foreign keys and indexes in one step.
DROP SCHEMA IF EXISTS oauth CASCADE;

COMMIT;
