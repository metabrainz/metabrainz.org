#!/usr/bin/env bash
exec 2>&1
set -e

# Disable IPV6 to silence "Network is unreachable" errors.
postconf -e "inet_protocols = ipv4"
postconf -e "myorigin = metabrainz.org"
postconf -e "relay_domains = metabrainz.org"

# http://serverfault.com/a/655127
# It seems that /etc/resolv.conf changes once the container is started, so
# this is not inside the Dockerfile.
cp -f /etc/resolv.conf /var/spool/postfix/etc/resolv.conf
cp -f /etc/services /var/spool/postfix/etc/services

# Adjust `mynetworks` so that we can relay mail from the MBS containers.
DOCKER_NETWORK=$(getent hosts postfix | awk '{ print $1 }' | sed 's/[0-9]\+$/0\/24/g')
MY_NETWORKS=$(postconf -d mynetworks)
postconf -e "$MY_NETWORKS $DOCKER_NETWORK"

# `rsyslogd` creates /var/log/syslog.
rsyslogd
postfix start
exec tail -F /var/log/syslog
