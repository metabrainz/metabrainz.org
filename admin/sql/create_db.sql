\set ON_ERROR_STOP 1

-- Create the user and the database. Must run as user postgres.

CREATE USER metabrainz NOCREATEDB NOSUPERUSER;
CREATE DATABASE metabrainz WITH OWNER = metabrainz TEMPLATE template0 ENCODING = 'UNICODE';
