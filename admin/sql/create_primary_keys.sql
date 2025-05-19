BEGIN;

ALTER TABLE tier ADD CONSTRAINT tier_pkey PRIMARY KEY (id);
ALTER TABLE supporter ADD CONSTRAINT supporter_pkey PRIMARY KEY (id);
ALTER TABLE token ADD CONSTRAINT token_pkey PRIMARY KEY (value);
ALTER TABLE token_log ADD CONSTRAINT token_log_pkey PRIMARY KEY (token_value, "timestamp", action);
ALTER TABLE access_log ADD CONSTRAINT access_log_pkey PRIMARY KEY (token, "timestamp");
ALTER TABLE payment ADD CONSTRAINT payment_pkey PRIMARY KEY (id);
ALTER TABLE dataset ADD CONSTRAINT dataset_pkey PRIMARY KEY (id);
ALTER TABLE dataset_supporter ADD CONSTRAINT dataset_supporter_pkey PRIMARY KEY (id);
ALTER TABLE notification ADD CONSTRAINT notification_pkey PRIMARY KEY (id);
ALTER TABLE user_preference ADD CONSTRAINT user_preference_pkey PRIMARY KEY (id);

COMMIT;
