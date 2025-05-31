BEGIN;

-- Add the nonce field to the code table for OpenID Connect
ALTER TABLE oauth.code ADD COLUMN nonce TEXT;
INSERT INTO oauth.scope (name, description)
     VALUES ('openid', 'Sign you in and view your unique user id');

COMMIT; 