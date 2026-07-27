BEGIN;

-- Unique indexes (natural keys that were previously inline UNIQUE constraints).
CREATE UNIQUE INDEX scope_name_uniq_idx ON oauth.scope (name);
CREATE UNIQUE INDEX client_client_id_uniq_idx ON oauth.client (client_id);
CREATE UNIQUE INDEX code_code_uniq_idx ON oauth.code (code);
CREATE UNIQUE INDEX access_token_uniq_idx ON oauth.access_token (access_token);
CREATE UNIQUE INDEX refresh_token_uniq_idx ON oauth.refresh_token (refresh_token);

-- Foreign key column indexes.
CREATE INDEX client_owner_id_idx ON oauth.client (owner_id);

CREATE INDEX code_user_id_idx ON oauth.code (user_id);
CREATE INDEX code_client_id_idx ON oauth.code (client_id);

CREATE INDEX access_token_user_id_idx ON oauth.access_token (user_id);
CREATE INDEX access_token_client_id_idx ON oauth.access_token (client_id);
CREATE INDEX access_token_authorization_code_id_idx ON oauth.access_token (authorization_code_id);

CREATE INDEX refresh_token_user_id_idx ON oauth.refresh_token (user_id);
CREATE INDEX refresh_token_client_id_idx ON oauth.refresh_token (client_id);
CREATE INDEX refresh_token_authorization_code_id_idx ON oauth.refresh_token (authorization_code_id);

CREATE INDEX l_access_token_scope_access_token_id_idx ON oauth.l_access_token_scope (access_token_id);
CREATE INDEX l_access_token_scope_scope_id_idx ON oauth.l_access_token_scope (scope_id);

CREATE INDEX l_refresh_token_scope_refresh_token_id_idx ON oauth.l_refresh_token_scope (refresh_token_id);
CREATE INDEX l_refresh_token_scope_scope_id_idx ON oauth.l_refresh_token_scope (scope_id);

CREATE INDEX l_code_scope_code_id_idx ON oauth.l_code_scope (code_id);
CREATE INDEX l_code_scope_scope_id_idx ON oauth.l_code_scope (scope_id);

COMMIT;
