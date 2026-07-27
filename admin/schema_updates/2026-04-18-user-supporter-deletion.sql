BEGIN;

ALTER TABLE dataset_supporter DROP CONSTRAINT dataset_supporter_supporter_id_fkey;
ALTER TABLE dataset_supporter
    ADD CONSTRAINT dataset_supporter_supporter_id_fkey FOREIGN KEY (supporter_id)
    REFERENCES supporter (id) MATCH SIMPLE
    ON UPDATE NO ACTION ON DELETE CASCADE;

ALTER TABLE dataset_supporter DROP CONSTRAINT dataset_supporter_dataset_id_fkey;
ALTER TABLE dataset_supporter
    ADD CONSTRAINT dataset_supporter_dataset_id_fkey FOREIGN KEY (dataset_id)
    REFERENCES dataset (id) MATCH SIMPLE
    ON UPDATE NO ACTION ON DELETE CASCADE;

COMMIT;
