#!/usr/bin/env bash

apt-get update
apt-get install -y build-essential python-virtualenv python-dev git curl

# Less compiler
curl -sL https://deb.nodesource.com/setup | sudo bash -
apt-get install -y nodejs
npm install -g less

cd /vagrant
pip install -r requirements.txt
