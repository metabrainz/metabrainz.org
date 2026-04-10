BEGIN;

ALTER TABLE payment ADD COLUMN supporter_id INTEGER;

ALTER TABLE payment
  ADD CONSTRAINT payment_supporter_id_fkey FOREIGN KEY (supporter_id)
  REFERENCES supporter (id) MATCH SIMPLE
  ON UPDATE CASCADE ON DELETE SET NULL;

CREATE INDEX payment_supporter_id_idx ON payment (supporter_id);

COMMIT;
