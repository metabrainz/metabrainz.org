BEGIN;

ALTER TABLE oauth.client
    ADD CONSTRAINT client_owner_id_fkey FOREIGN KEY (owner_id)
    REFERENCES "user" (id) ON DELETE CASCADE;

ALTER TABLE oauth.code
    ADD CONSTRAINT code_user_id_fkey FOREIGN KEY (user_id)
    REFERENCES "user" (id) ON DELETE CASCADE;

ALTER TABLE oauth.code
    ADD CONSTRAINT code_client_id_fkey FOREIGN KEY (client_id)
    REFERENCES oauth.client (id) ON DELETE CASCADE;

ALTER TABLE oauth.access_token
    ADD CONSTRAINT access_token_user_id_fkey FOREIGN KEY (user_id)
    REFERENCES "user" (id) ON DELETE CASCADE;

ALTER TABLE oauth.access_token
    ADD CONSTRAINT access_token_client_id_fkey FOREIGN KEY (client_id)
    REFERENCES oauth.client (id) ON DELETE CASCADE;

ALTER TABLE oauth.access_token
    ADD CONSTRAINT access_token_authorization_code_id_fkey FOREIGN KEY (authorization_code_id)
    REFERENCES oauth.code (id) ON DELETE CASCADE;

ALTER TABLE oauth.refresh_token
    ADD CONSTRAINT refresh_token_user_id_fkey FOREIGN KEY (user_id)
    REFERENCES "user" (id) ON DELETE CASCADE;

ALTER TABLE oauth.refresh_token
    ADD CONSTRAINT refresh_token_client_id_fkey FOREIGN KEY (client_id)
    REFERENCES oauth.client (id) ON DELETE CASCADE;

ALTER TABLE oauth.refresh_token
    ADD CONSTRAINT refresh_token_authorization_code_id_fkey FOREIGN KEY (authorization_code_id)
    REFERENCES oauth.code (id) ON DELETE CASCADE;

ALTER TABLE oauth.l_access_token_scope
    ADD CONSTRAINT l_access_token_scope_access_token_id_fkey FOREIGN KEY (access_token_id)
    REFERENCES oauth.access_token (id) ON DELETE CASCADE;

ALTER TABLE oauth.l_access_token_scope
    ADD CONSTRAINT l_access_token_scope_scope_id_fkey FOREIGN KEY (scope_id)
    REFERENCES oauth.scope (id) ON DELETE CASCADE;

ALTER TABLE oauth.l_refresh_token_scope
    ADD CONSTRAINT l_refresh_token_scope_refresh_token_id_fkey FOREIGN KEY (refresh_token_id)
    REFERENCES oauth.refresh_token (id) ON DELETE CASCADE;

ALTER TABLE oauth.l_refresh_token_scope
    ADD CONSTRAINT l_refresh_token_scope_scope_id_fkey FOREIGN KEY (scope_id)
    REFERENCES oauth.scope (id) ON DELETE CASCADE;

ALTER TABLE oauth.l_code_scope
    ADD CONSTRAINT l_code_scope_code_id_fkey FOREIGN KEY (code_id)
    REFERENCES oauth.code (id) ON DELETE CASCADE;

ALTER TABLE oauth.l_code_scope
    ADD CONSTRAINT l_code_scope_scope_id_fkey FOREIGN KEY (scope_id)
    REFERENCES oauth.scope (id) ON DELETE CASCADE;

COMMIT;
