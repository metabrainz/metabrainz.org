BEGIN;

CREATE TYPE dataset_project_type AS ENUM ('musicbrainz', 'listenbrainz');

CREATE TABLE dataset (
    id          INTEGER GENERATED ALWAYS AS IDENTITY,
    name        TEXT NOT NULL,
    description TEXT,
    project     dataset_project_type NOT NULL
);

CREATE TABLE dataset_user (
    id          INTEGER GENERATED ALWAYS AS IDENTITY,
    user_id     INTEGER NOT NULL,
    dataset_id  INTEGER NOT NULL
);

ALTER TABLE dataset ADD CONSTRAINT dataset_pkey PRIMARY KEY (id);
ALTER TABLE dataset_user ADD CONSTRAINT dataset_user_pkey PRIMARY KEY (id);

ALTER TABLE dataset_user
    ADD CONSTRAINT dataset_user_user_id_fkey FOREIGN KEY (user_id)
    REFERENCES "user" (id) MATCH SIMPLE
    ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE dataset_user
    ADD CONSTRAINT dataset_user_dataset_id_fkey FOREIGN KEY (dataset_id)
    REFERENCES "dataset" (id) MATCH SIMPLE
    ON UPDATE NO ACTION ON DELETE NO ACTION;

COMMIT;
