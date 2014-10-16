#!/usr/bin/env bash

apt-get update
apt-get install -y build-essential python-virtualenv python-dev git curl

# PostgreSQL
PG_VERSION=9.1
apt-get -y install "postgresql-$PG_VERSION" "postgresql-contrib-$PG_VERSION" "postgresql-server-dev-$PG_VERSION"
PG_CONF="/etc/postgresql/$PG_VERSION/main/postgresql.conf"
PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
PG_DIR="/var/lib/postgresql/$PG_VERSION/main"

# Setting up PostgreSQL access
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF"
echo "host all all all trust" >> "$PG_HBA"
service postgresql restart

# Less compiler
curl -sL https://deb.nodesource.com/setup | sudo bash -
apt-get install -y nodejs
npm install -g less

cd /vagrant
pip install -r requirements.txt
