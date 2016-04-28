BEGIN;

CREATE TABLE tier (
  id         SERIAL            NOT NULL, -- PK
  name       CHARACTER VARYING NOT NULL,
  short_desc TEXT,
  long_desc  TEXT,
  price      NUMERIC(11, 2)    NOT NULL,
  available  BOOLEAN           NOT NULL,
  "primary"  BOOLEAN           NOT NULL
);

CREATE TABLE "user" (
  id               SERIAL            NOT NULL, -- PK
  is_commercial    BOOLEAN           NOT NULL,
  musicbrainz_id   CHARACTER VARYING UNIQUE,
  created          TIMESTAMP WITH TIME ZONE,
  state            state_types       NOT NULL,
  contact_name     CHARACTER VARYING NOT NULL,
  contact_email    CHARACTER VARYING NOT NULL,
  data_usage_desc  TEXT,
  org_name         CHARACTER VARYING,
  org_logo_url     CHARACTER VARYING,
  website_url      CHARACTER VARYING,
  api_url          CHARACTER VARYING,
  org_desc         TEXT,
  address_street   CHARACTER VARYING,
  address_city     CHARACTER VARYING,
  address_state    CHARACTER VARYING,
  address_postcode CHARACTER VARYING,
  address_country  CHARACTER VARYING,
  tier_id          INTEGER,
  amount_pledged   NUMERIC(11, 2),
  good_standing    BOOLEAN           NOT NULL,
  in_deadbeat_club BOOLEAN           NOT NULL,
  featured         BOOLEAN           NOT NULL
);

CREATE TABLE token (
  value     CHARACTER VARYING NOT NULL, -- PK
  is_active BOOLEAN           NOT NULL,
  owner_id  INTEGER, -- FK
  created   TIMESTAMP WITH TIME ZONE
);

CREATE TABLE token_log (
  token_value CHARACTER VARYING        NOT NULL, -- PK
  "timestamp" TIMESTAMP WITH TIME ZONE NOT NULL, -- PK
  action      token_log_action_types   NOT NULL, -- PK
  user_id     INTEGER
);

CREATE TABLE access_log (
  token       CHARACTER VARYING        NOT NULL, -- PK
  "timestamp" TIMESTAMP WITH TIME ZONE NOT NULL, -- PK
  ip_address  INET
);

CREATE TABLE donation (
  id               SERIAL, -- PK
  first_name       CHARACTER VARYING NOT NULL,
  last_name        CHARACTER VARYING NOT NULL,
  email            CHARACTER VARYING NOT NULL,
  editor_name      CHARACTER VARYING,
  can_contact      BOOLEAN,
  anonymous        BOOLEAN,
  address_street   CHARACTER VARYING,
  address_city     CHARACTER VARYING,
  address_state    CHARACTER VARYING,
  address_postcode CHARACTER VARYING,
  address_country  CHARACTER VARYING,
  payment_date     TIMESTAMP WITH TIME ZONE,
  payment_method   payment_method_types,
  transaction_id   CHARACTER VARYING,
  amount           NUMERIC(11, 2)    NOT NULL,
  fee              NUMERIC(11, 2),
  memo             CHARACTER VARYING,
  is_donation      BOOLEAN           NOT NULL,
  invoice_number   INTEGER
);

COMMIT;
