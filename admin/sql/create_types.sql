CREATE TYPE payment_method_types AS ENUM (
  'stripe',
  'paypal',
  'wepay', -- legacy
  'bitcoin',
  'check'
);

CREATE TYPE state_types AS ENUM (
  'active',
  'pending',
  'waiting',
  'rejected',
  'limited'
);

CREATE TYPE token_log_action_types AS ENUM (
  'deactivate',
  'create'
);

CREATE TYPE payment_currency AS ENUM (
  'usd',
  'eur'
);

CREATE TYPE dataset_project_type AS ENUM (
  'musicbrainz',
  'listenbrainz',
  'critiquebrainz'
);

CREATE TYPE notification_project_type AS ENUM (
    'metabrainz',
    'musicbrainz',
    'listenbrainz',
    'bookbrainz',
    'critiquebrainz'
);
