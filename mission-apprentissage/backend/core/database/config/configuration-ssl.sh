#!/usr/bin/env bash

set -e


# Initialize SSL directory
mkdir /var/lib/postgresql/data/ssl/

# Override the default configuration using additional configuration files
if [ ! -f /var/lib/postgresql/data/postgresql.conf ]; then
    echo "[WARNING] No such file '/var/lib/postgresql/data/postgresql.conf'" >&2
elif [ ! -d /opt/postgresql.conf.d ]; then
    echo "[WARNING] No such directory '/opt/postgresql.conf.d'" >&2
else
    sed -r "s@^#include_dir.*\$@include_dir = '/opt/postgresql.conf.d/'@" -i /var/lib/postgresql/data/postgresql.conf
fi


# Copy SSL files to protected directory and override permissions
if [ -d /opt/ssl-in ] && [ -n "$(ls -A /opt/ssl-in 2>/dev/null)" ]; then
    cp -r /opt/ssl-in/* /var/lib/postgresql/data/ssl/
else
    echo "[INFO] Generating self-signed SSL certificate"
    openssl req -new -x509 -days 3650 -nodes \
        -out /var/lib/postgresql/data/ssl/server.crt \
        -keyout /var/lib/postgresql/data/ssl/server.key \
        -subj "/CN=postgres"
fi

find /var/lib/postgresql/data/ssl/ -type f -exec chmod 600 {} \;
chown -R postgres:postgres /var/lib/postgresql/data/ssl/