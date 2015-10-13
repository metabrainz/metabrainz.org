#!/bin/sh -e

apt-get update
apt-get -y upgrade
apt-get install -y python-virtualenv python-dev memcached


# Setting up PostgreSQL
PG_VERSION=9.3

apt-get -y install "postgresql-$PG_VERSION" "postgresql-contrib-$PG_VERSION" "postgresql-server-dev-$PG_VERSION"
PG_CONF="/etc/postgresql/$PG_VERSION/main/postgresql.conf"
PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
PG_DIR="/var/lib/postgresql/$PG_VERSION/main"

# Setting up PostgreSQL access
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF"
echo "host all all all trust" >> "$PG_HBA"

# Explicitly set default client_encoding
echo "client_encoding = utf8" >> "$PG_CONF"

service postgresql restart

# Mail server
DEBIAN_FRONTEND=noninteractive apt-get install -y postfix   

# Less compiler
curl -sL https://deb.nodesource.com/setup | sudo bash -
apt-get install -y nodejs
npm install -g less less-plugin-clean-css

# Required libraries for Python packages
apt-get install -y libtiff5-dev

cd /vagrant
easy_install -U pip
pip install -r requirements.txt
python manage.py create_db
python manage.py create_tables
