-- Create the user and the database. Must run as user postgres.

CREATE USER metabrainz NOCREATEDB NOSUPERUSER;
ALTER USER metabrainz WITH PASSWORD 'metabrainz';
CREATE DATABASE metabrainz WITH OWNER = metabrainz TEMPLATE template0 ENCODING = 'UNICODE';
