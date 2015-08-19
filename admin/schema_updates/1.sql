BEGIN;

CREATE TYPE payment_method_types AS ENUM ('stripe', 'paypal', 'wepay');
ALTER TABLE donation ADD COLUMN payment_method payment_method_types;
ALTER TABLE donation DROP COLUMN method;

ALTER TABLE donation RENAME COLUMN contact TO can_contact;
ALTER TABLE donation RENAME COLUMN anon TO anonymous;

END;
