BEGIN;

CREATE TABLE domain_blacklist (
    id                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    domain             TEXT NOT NULL UNIQUE,
    reason             TEXT,
    created_at         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMIT;
