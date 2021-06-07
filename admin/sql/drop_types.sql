BEGIN;

DROP TYPE IF EXISTS payment_method_types CASCADE;
DROP TYPE IF EXISTS payment_currency CASCADE;
DROP TYPE IF EXISTS state_types CASCADE;
DROP TYPE IF EXISTS token_log_action_types CASCADE;

COMMIT;
