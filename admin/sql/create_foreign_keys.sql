BEGIN;

ALTER TABLE token
  ADD CONSTRAINT token_owner_id_fkey FOREIGN KEY (owner_id)
  REFERENCES supporter (id) MATCH SIMPLE
  ON UPDATE CASCADE ON DELETE SET NULL;

ALTER TABLE supporter
  ADD CONSTRAINT supporter_user_id_fkey FOREIGN KEY (user_id)
  REFERENCES "user" (id) MATCH SIMPLE
  ON UPDATE CASCADE ON DELETE SET NULL;

ALTER TABLE supporter
  ADD CONSTRAINT supporter_tier_id_fkey FOREIGN KEY (tier_id)
  REFERENCES tier (id) MATCH SIMPLE
  ON UPDATE CASCADE ON DELETE SET NULL;

ALTER TABLE dataset_supporter
    ADD CONSTRAINT dataset_supporter_supporter_id_fkey FOREIGN KEY (supporter_id)
    REFERENCES supporter (id) MATCH SIMPLE
    ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE dataset_supporter
    ADD CONSTRAINT dataset_supporter_dataset_id_fkey FOREIGN KEY (dataset_id)
    REFERENCES "dataset" (id) MATCH SIMPLE
    ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE token_log
  ADD CONSTRAINT token_log_token_value_fkey FOREIGN KEY (token_value)
  REFERENCES token (value) MATCH SIMPLE
  ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE token_log
  ADD CONSTRAINT token_log_supporter_id_fkey FOREIGN KEY (supporter_id)
  REFERENCES supporter (id) MATCH SIMPLE
  ON UPDATE CASCADE ON DELETE SET NULL;

ALTER TABLE access_log
  ADD CONSTRAINT access_log_token_fkey FOREIGN KEY (token)
  REFERENCES token (value) MATCH SIMPLE
  ON UPDATE NO ACTION ON DELETE NO ACTION;

COMMIT;
