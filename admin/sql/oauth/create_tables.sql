CREATE TABLE oauth.client (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    client_id           TEXT    NOT NULL, -- PK
    client_secret       TEXT,  -- public clients won't have client_secret so NULLABLE
    owner_id            INTEGER, -- (maybe FK?), user
    client_name         TEXT    NOT NULL,
    description         TEXT    NOT NULL,
    website             TEXT    NOT NULL,
    redirect_uris       TEXT[]  NOT NULL
);

CREATE TABLE oauth.scopes (
    id          INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL, -- PK
    name        TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE oauth.token (
    id              INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL, -- PK
    user_id         INTEGER NOT NULL, -- FK, user
    client_id       INTEGER NOT NULL, -- FK, client
    access_token    TEXT NOT NULL,
    refresh_token   TEXT,
    scopes          INTEGER[] NOT NULL,
    issued_at       TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    expires_in      INTEGER NOT NULL,
    revoked         BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE oauth.code (
    id              INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL, -- PK
    user_id         INTEGER NOT NULL, -- FK, user
    client_id       INTEGER NOT NULL, -- FK, client
    code            TEXT NOT NULL UNIQUE,
    redirect_uri    TEXT NOT NULL,
    response_type   TEXT NOT NULL,
    scopes          INTEGER[] NOT NULL,
    code_challenge  TEXT,
    code_challenge_method TEXT,
    granted_at      TIMESTAMP WITHOUT TIME ZONE NOT NULL
);

 -- TODO: add relevant fields to user model
CREATE TABLE oauth."user" (
    id              INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL
);

