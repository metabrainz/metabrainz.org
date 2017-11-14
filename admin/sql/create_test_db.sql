\set ON_ERROR_STOP 1

-- Create the user and the database. Must run as user postgres.

CREATE USER meb_test NOCREATEDB NOSUPERUSER;
CREATE DATABASE meb_test WITH OWNER = meb_test TEMPLATE template0 ENCODING = 'UNICODE';
