#!/usr/bin/env bash

apt-get update
apt-get install -y python-virtualenv python-dev git

cd /vagrant
pip install -r requirements.txt
