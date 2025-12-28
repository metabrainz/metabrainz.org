BEGIN;

ALTER TABLE supporter DROP CONSTRAINT supporter_user_id_fkey;
ALTER TABLE supporter ADD CONSTRAINT supporter_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES "user" (id)
    ON UPDATE CASCADE ON DELETE RESTRICT;

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

ALTER TYPE moderation_action_type ADD VALUE 'delete';
