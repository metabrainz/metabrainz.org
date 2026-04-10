BEGIN;

CREATE INDEX payment_supporter_id_idx ON payment (supporter_id);

COMMIT;
