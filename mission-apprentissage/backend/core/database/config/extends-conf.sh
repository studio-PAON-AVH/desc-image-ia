#!/usr/bin/env bash
# /extends-conf.sh

set -e


if [ ! -f /var/lib/postgresql/data/postgresql.conf ]; then
  echo "[WARNING] No such file '/var/lib/postgresql/data/postgresql.conf'" >&2
else
  sed -r "s@^#include_dir.*\$@include_dir = '/opt/postgresql.conf.d/'@" \
    -i /var/lib/postgresql/data/postgresql.conf
fi