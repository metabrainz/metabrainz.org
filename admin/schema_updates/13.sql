BEGIN;

CREATE TABLE oauth_client (
  client_id     CHARACTER VARYING, -- PK
  client_secret CHARACTER VARYING NOT NULL,
  redirect_uri  CHARACTER VARYING NOT NULL,
  user_id       INTEGER           NOT NULL, -- FK, user
  name          CHARACTER VARYING NOT NULL,
  description   CHARACTER VARYING NOT NULL,
  website       CHARACTER VARYING NOT NULL
);

CREATE TABLE oauth_grant (
  id           SERIAL                   NOT NULL, -- PK
  client_id    CHARACTER VARYING        NOT NULL, -- FK, oauth_client
  user_id      INTEGER                  NOT NULL, -- FK, user
  redirect_uri CHARACTER VARYING        NOT NULL,
  code         CHARACTER VARYING        NOT NULL,
  expires      TIMESTAMP WITH TIME ZONE NOT NULL,
  scopes       CHARACTER VARYING
);

CREATE TABLE oauth_token (
  id            SERIAL                   NOT NULL, -- PK
  client_id     CHARACTER VARYING        NOT NULL, -- FK, oauth_client
  access_token  CHARACTER VARYING        NOT NULL,
  user_id       INT                      NOT NULL, -- FK, user
  refresh_token CHARACTER VARYING        NOT NULL,
  expires       TIMESTAMP WITH TIME ZONE NOT NULL,
  scopes        CHARACTER VARYING
);


ALTER TABLE oauth_client ADD CONSTRAINT oauth_client_pkey PRIMARY KEY (client_id);
ALTER TABLE oauth_grant ADD CONSTRAINT oauth_grant_pkey PRIMARY KEY (id);
ALTER TABLE oauth_token ADD CONSTRAINT oauth_token_pkey PRIMARY KEY (id);


ALTER TABLE oauth_client
  ADD CONSTRAINT oauth_client_user_fkey FOREIGN KEY (user_id)
REFERENCES "user" (id) MATCH SIMPLE
ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE oauth_grant
  ADD CONSTRAINT oauth_grant_oauth_client_fkey FOREIGN KEY (client_id)
REFERENCES oauth_client (client_id) MATCH SIMPLE
ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE oauth_grant
  ADD CONSTRAINT oauth_grant_user_fkey FOREIGN KEY (user_id)
REFERENCES "user" (id) MATCH SIMPLE
ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE oauth_token
  ADD CONSTRAINT oauth_token_oauth_client_fkey FOREIGN KEY (client_id)
REFERENCES oauth_client (client_id) MATCH SIMPLE
ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE oauth_token
  ADD CONSTRAINT oauth_token_user_fkey FOREIGN KEY (user_id)
REFERENCES "user" (id) MATCH SIMPLE
ON UPDATE CASCADE ON DELETE CASCADE;

COMMIT;
