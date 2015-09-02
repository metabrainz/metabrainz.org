BEGIN;

CREATE TYPE token_log_action_types AS ENUM (
  'deactivate',
  'create'
);

CREATE TABLE token_log (
  token_value CHARACTER VARYING        NOT NULL,
  "timestamp" TIMESTAMP WITH TIME ZONE NOT NULL,
  action      token_log_action_types   NOT NULL,
  user_id     INTEGER                  NOT NULL,
  CONSTRAINT token_log_pkey PRIMARY KEY (token_value, "timestamp", action),
  CONSTRAINT token_log_token_fkey FOREIGN KEY (token_value)
    REFERENCES token (value) MATCH SIMPLE
    ON UPDATE NO ACTION ON DELETE NO ACTION,
  CONSTRAINT token_log_user_id_fkey FOREIGN KEY (user_id)
    REFERENCES "user" (id) MATCH SIMPLE
    ON UPDATE CASCADE ON DELETE SET NULL
);

COMMIT;
