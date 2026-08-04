ALTER TYPE moderation_action_type ADD VALUE 'change_email';

BEGIN;

-- Back the case insensitive duplicate address lookups. Not unique: an address may
-- legitimately be shared between accounts, and a plain btree cannot serve LOWER().
CREATE INDEX user_email_idx ON "user" (LOWER(email));
CREATE INDEX user_unconfirmed_email_idx ON "user" (LOWER(unconfirmed_email));

COMMIT;
