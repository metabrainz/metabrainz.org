BEGIN;

-- Normalize stored addresses for the lowercase email lookups in recovery forms.
-- Verification and password-reset links tied to changed addresses must be requested
-- again because their checksums include the stored email address.
UPDATE "user"
SET email = LOWER(TRIM(email)),
    unconfirmed_email = LOWER(TRIM(unconfirmed_email))
WHERE email IS DISTINCT FROM LOWER(TRIM(email))
   OR unconfirmed_email IS DISTINCT FROM LOWER(TRIM(unconfirmed_email));

COMMIT;
