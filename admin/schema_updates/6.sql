BEGIN;

ALTER TYPE payment_method_types ADD VALUE 'bitcoin';
ALTER TYPE payment_method_types ADD VALUE 'check';

BEGIN;
