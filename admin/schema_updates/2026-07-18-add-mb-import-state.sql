BEGIN;

CREATE TABLE mb_import_state (
    importer                TEXT NOT NULL,
    last_updated            TIMESTAMP WITH TIME ZONE NOT NULL
);

ALTER TABLE mb_import_state ADD CONSTRAINT mb_import_state_pkey PRIMARY KEY (importer);

COMMIT;
