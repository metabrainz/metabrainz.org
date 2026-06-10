BEGIN;

ALTER TABLE oauth.scope ADD CONSTRAINT scope_pkey PRIMARY KEY (id);
ALTER TABLE oauth.client ADD CONSTRAINT client_pkey PRIMARY KEY (id);
ALTER TABLE oauth.code ADD CONSTRAINT code_pkey PRIMARY KEY (id);
ALTER TABLE oauth.access_token ADD CONSTRAINT access_token_pkey PRIMARY KEY (id);
ALTER TABLE oauth.refresh_token ADD CONSTRAINT refresh_token_pkey PRIMARY KEY (id);
ALTER TABLE oauth.l_access_token_scope ADD CONSTRAINT l_access_token_scope_pkey PRIMARY KEY (id);
ALTER TABLE oauth.l_refresh_token_scope ADD CONSTRAINT l_refresh_token_scope_pkey PRIMARY KEY (id);
ALTER TABLE oauth.l_code_scope ADD CONSTRAINT l_code_scope_pkey PRIMARY KEY (id);

COMMIT;
