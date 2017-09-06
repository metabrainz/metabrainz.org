BEGIN;

CREATE TYPE payment_currency AS ENUM (
  'usd',
  'eur'
);

ALTER TABLE payment ADD COLUMN currency payment_currency;

-- All existing payments were in USD, so we can just set them to that.
UPDATE payment SET currency = 'usd';

ALTER TABLE payment ALTER COLUMN currency SET NOT NULL;

COMMIT;
